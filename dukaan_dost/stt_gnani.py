"""
stt_gnani.py

Gnani Prisma speech-to-text over the realtime WebSocket. Presents the
same warmup() / start_streaming_session() interface as stt_sarvam.py
(StreamingSession: feed(), finish() -> (transcript, language_code),
latest_partial), so STT_PROVIDER=gnani is a drop-in switch.

Protocol, read from docs.gnani.ai/api/STT/stt-websocket.md on 2026-11-02:
  - URL wss://api.vachana.ai/stt/v3/stream; every setting is an upgrade
    header (language_code, model, format, keyterms, x-sample-rate, the
    x-min-silence-ms family, ...).
  - Audio is raw s16le mono in frames of EXACTLY 1,024 bytes (512
    samples), sent at real-time pace (32 ms per frame at 16 kHz).
  - Server JSON: connected, speech_start, processing, transcript
    (text, is_final, detected_language_code on v3.0), error.
  - The client may send {"type": "commit"}, which closes the open
    utterance at once without waiting for silence. There is no
    end-of-session message; the session ends by closing the socket.

NOT YET RUN AGAINST THE REAL SERVICE. No Gnani key was available when this
was written; the tests (tests/test_stt_gnani.py) run it against a local
stand-in server that follows the documented protocol. Run
scripts/gnani_smoke_test.py with a real key before trusting it on a call.

Two doc inconsistencies are handled rather than guessed at:
  - The Prisma v3.0 model page names the headers lang_code / x-model /
    x-format / x-keyterms, the WebSocket page names language_code / model /
    format / keyterms. The WebSocket page says that when both spellings are
    sent the new one wins, so BOTH are sent.
  - Whether the 'commit' frame exists on v3.0 was in doubt (the model page
    does not mention it). The WebSocket page documents it for all models.
    If a server ignored it, finish() still ends: it also sends trailing
    silence so the server's own VAD closes the segment.

One WebSocket per utterance (like stt_sarvam.py): the app does its own
end-of-speech detection and hands over one utterance at a time.
"""

import asyncio
import json
import logging
import os
import queue
import threading
import time

log = logging.getLogger("stt_gnani")

SAMPLE_RATE = 16000
FRAME_BYTES = 1024                    # 512 samples of s16le: required exactly
FRAME_SEC = FRAME_BYTES / 2 / SAMPLE_RATE      # 0.032 s of audio per frame
# Audio the server may receive ahead of real time. The recorder hands over
# a short run of pre-roll audio in one go when an utterance starts; the docs
# say sustained bursts hurt the server's VAD, so only this much is allowed.
BURST_ALLOWANCE_SEC = float(os.getenv("GNANI_STT_BURST_ALLOWANCE_SEC", "0.5"))
# Trailing silence sent with the commit, in case a server ignores the commit
# frame and relies on its own VAD (min silence defaults to 500 ms).
TRAILING_SILENCE_SEC = float(os.getenv("GNANI_STT_TRAILING_SILENCE_SEC", "0.6"))
# After commit, how long to wait for a late "processing" before concluding
# that nothing more is coming (e.g. the whole utterance was already closed
# by the server's own silence detection).
COMMIT_GRACE_SEC = float(os.getenv("GNANI_STT_COMMIT_GRACE_SEC", "0.3"))
STREAMING_FINISH_TIMEOUT_SEC = float(os.getenv("GNANI_STT_FINISH_TIMEOUT_SEC", "8"))
CONNECT_TIMEOUT_SEC = float(os.getenv("GNANI_STT_CONNECT_TIMEOUT_SEC", "10"))

# Languages this deployment serves; anything else is treated as noise (the
# same guard stt_sarvam.py has against cross-language hallucinations).
SUPPORTED_LANGUAGE_CODES = {
    c.strip().lower() for c in os.getenv("GNANI_SUPPORTED_LANGUAGES", "en-in,hi-in,te-in").split(",") if c.strip()
}

# Not documented: the real concurrent-session cap (shown at app.gnani.ai). Kept
# small until measured (experiment E5).
GNANI_MAX_CONCURRENT_SESSIONS = int(os.getenv("GNANI_STT_MAX_CONCURRENT_SESSIONS", "4"))
_concurrency = threading.Semaphore(GNANI_MAX_CONCURRENT_SESSIONS)

_keyterms: list = []
_keyterms_lock = threading.Lock()


def _url() -> str:
    return os.getenv("GNANI_STT_URL", "wss://api.vachana.ai/stt/v3/stream")


def _api_key() -> str:
    key = os.environ.get("GNANI_API_KEY", "")
    if not key:
        raise RuntimeError("GNANI_API_KEY is not set. Get a key at https://app.gnani.ai/voice.")
    return key


def set_keyterms(terms) -> int:
    """
    Product names to boost (Prisma v3.0 keyterms, up to 200). HTTP headers are
    ASCII, so non-ASCII terms are skipped and written Latin-script names
    (Maggi, Amul, Tata) are kept. Returns how many were kept.
    """
    kept, seen = [], set()
    for t in terms or []:
        t = " ".join(str(t).split())
        if not t or "," in t or t.lower() in seen:
            continue
        if not t.isascii() or "<|" in t or "|>" in t:
            continue
        seen.add(t.lower())
        kept.append(t)
        if len(kept) == 200:
            break
    with _keyterms_lock:
        _keyterms[:] = kept
    return len(kept)


def _normalize_language(language_code: str | None) -> str:
    """'hi-in' / 'hi_IN' / 'hi' -> 'hi-IN'; None -> the default hint list."""
    if not language_code or language_code.lower() in ("unknown", "auto", "indic-auto"):
        return os.getenv("GNANI_STT_LANGUAGES", "hi-IN,en-IN,te-IN")
    code = language_code.replace("_", "-")
    lang, _, region = code.partition("-")
    return f"{lang.lower()}-{(region or 'IN').upper()}"


def _build_headers(language: str) -> dict:
    fmt = os.getenv("GNANI_STT_FORMAT", "transcribe")
    model = os.getenv("GNANI_STT_MODEL", "prisma-v3.0")
    headers = {
        "x-api-key-id": _api_key(),
        "language_code": language, "lang_code": language,
        "model": model, "x-model": model,
        "format": fmt, "x-format": fmt,
        "x-sample-rate": str(SAMPLE_RATE),
    }
    with _keyterms_lock:
        terms = list(_keyterms)
    env_terms = os.getenv("GNANI_STT_KEYTERMS", "")
    if not terms and env_terms:
        terms = [t for t in env_terms.split(",") if t.strip()]
    if terms:
        joined = ",".join(terms)
        headers["keyterms"] = joined
        headers["x-keyterms"] = joined
    for env, header in (("GNANI_STT_MIN_SILENCE_MS", "x-min-silence-ms"),
                        ("GNANI_STT_VAD_THRESHOLD", "x-vad-threshold"),
                        ("GNANI_STT_MIN_SPEECH_MS", "x-min-speech-ms")):
        if os.getenv(env):
            headers[header] = os.environ[env]
    return headers


def warmup():
    """Checks that a key is present. A real check needs a network call, which
    scripts/gnani_smoke_test.py does."""
    _api_key()
    log.info(f"[STT-GNANI] Key present, model={os.getenv('GNANI_STT_MODEL', 'prisma-v3.0')} "
             f"format={os.getenv('GNANI_STT_FORMAT', 'transcribe')} url={_url()}")


class StreamingSession:
    """
    One utterance, one WebSocket. A background thread owns an asyncio loop;
    feed() (called from the recorder thread) only puts bytes on a queue.
    """

    def __init__(self, language_code: str | None = None, is_stale=None):
        self._language = _normalize_language(language_code)
        self._locked = language_code is not None and "," not in self._language
        self._is_stale = is_stale
        self._sync_queue: queue.Queue = queue.Queue()
        self._segments: list = []
        self._detected_language = ""
        self._error = None
        self.latest_partial = ""
        self._thread = threading.Thread(target=self._run_thread, daemon=True, name="stt-gnani")
        self._thread.start()

    def feed(self, chunk: bytes) -> None:
        self._sync_queue.put(chunk)

    def finish(self) -> tuple[str, str]:
        self._sync_queue.put(None)
        self._thread.join(timeout=STREAMING_FINISH_TIMEOUT_SEC + CONNECT_TIMEOUT_SEC + 2)
        if self._thread.is_alive():
            log.error("[STT-GNANI] Timed out waiting for the result.")
            return "", "ERROR"
        if isinstance(self._error, str) and self._error.startswith("stale"):
            return "", ""
        if self._error and not self._segments:
            log.error(f"[STT-GNANI] {self._error}")
            return "", "ERROR"

        transcript = " ".join(s for s in self._segments if s).strip()
        language = self._detected_language or (self._language if self._locked else "")
        if transcript and language and language.lower() not in SUPPORTED_LANGUAGE_CODES:
            log.warning(f"[STT-GNANI] Discarding '{transcript}': tagged {language!r}, not a supported "
                        f"language (likely a hallucination from noise).")
            return "", ""
        if transcript and not language:
            language = self._language.split(",")[0]
        if transcript:
            log.info(f"[STT-GNANI] '{transcript}' (lang={language}, streaming)")
        else:
            log.info("[STT-GNANI] No speech recognized (streaming)")
        return transcript, language

    # -- thread / loop ---------------------------------------------------

    def _run_thread(self):
        while True:
            if self._is_stale is not None and self._is_stale():
                log.info("[STT-GNANI] Abandoning session while waiting for a slot: its call already ended.")
                self._error = "stale: call ended before a streaming slot freed up"
                return
            if _concurrency.acquire(timeout=0.5):
                break
        try:
            asyncio.run(self._run_async())
        except Exception as e:
            self._error = str(e) or type(e).__name__
        finally:
            _concurrency.release()

    async def _run_async(self):
        from websockets.asyncio.client import connect

        headers = _build_headers(self._language)
        loop = asyncio.get_running_loop()
        ws = await asyncio.wait_for(connect(_url(), additional_headers=headers, max_size=None),
                                    timeout=CONNECT_TIMEOUT_SEC)
        state = {"speech_open": False, "pending": 0, "commit_at": None, "last_event": time.monotonic()}
        done = asyncio.Event()

        async def receiver():
            try:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        continue
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    kind = msg.get("type")
                    state["last_event"] = time.monotonic()
                    if kind == "speech_start":
                        state["speech_open"] = True
                    elif kind == "processing":
                        state["speech_open"] = False
                        state["pending"] += 1
                    elif kind == "transcript":
                        state["pending"] = max(0, state["pending"] - 1)
                        text = (msg.get("text") or "").strip()
                        if text:
                            self._segments.append(text)
                            self.latest_partial = " ".join(self._segments)
                            if msg.get("detected_language_code"):
                                self._detected_language = msg["detected_language_code"]
                    elif kind == "error":
                        self._error = msg.get("message") or "error from the speech service"
                        log.error(f"[STT-GNANI] Server error: {self._error}")
                        done.set()
                        return
                    self._maybe_done(state, done)
            except Exception as e:
                if not done.is_set():
                    self._error = self._error or f"connection lost: {e}"
            finally:
                done.set()

        async def sender():
            buf = bytearray()
            sent = 0
            t0 = time.monotonic()

            async def send_frame(frame: bytes):
                nonlocal sent
                due = t0 + sent * FRAME_SEC - BURST_ALLOWANCE_SEC
                delay = due - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                await ws.send(bytes(frame))
                sent += 1

            while True:
                chunk = await loop.run_in_executor(None, self._sync_queue.get)
                if chunk is None:
                    break
                buf += chunk
                while len(buf) >= FRAME_BYTES:
                    await send_frame(buf[:FRAME_BYTES])
                    del buf[:FRAME_BYTES]
            # Utterance over: pad the last partial frame, then close the segment.
            if buf:
                await send_frame(bytes(buf) + b"\x00" * (FRAME_BYTES - len(buf)))
            await ws.send(json.dumps({"type": "commit"}))
            state["commit_at"] = time.monotonic()
            # Trailing silence for a server that ignores commit. It is sent without
            # pacing: commit already closed the segment, this is only the fallback.
            for _ in range(int(TRAILING_SILENCE_SEC / FRAME_SEC)):
                if done.is_set():
                    break
                await ws.send(b"\x00" * FRAME_BYTES)
            # The receiver decides when we are done; nudge it for the "nothing
            # came back" case.
            deadline = time.monotonic() + STREAMING_FINISH_TIMEOUT_SEC
            while not done.is_set() and time.monotonic() < deadline:
                self._maybe_done(state, done)
                await asyncio.sleep(0.05)
            done.set()

        recv_task = asyncio.create_task(receiver())
        send_task = asyncio.create_task(sender())
        try:
            await asyncio.wait_for(done.wait(), timeout=STREAMING_FINISH_TIMEOUT_SEC + 5)
        except asyncio.TimeoutError:
            self._error = self._error or "timed out waiting for the transcript"
        finally:
            for t in (send_task, recv_task):
                t.cancel()
            for t in (send_task, recv_task):
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
            try:
                await ws.close()
            except Exception:
                pass

    @staticmethod
    def _maybe_done(state: dict, done: asyncio.Event) -> None:
        """Done once commit was sent, every utterance the server started has
        produced its transcript, none is still open, and the grace period passed."""
        if state["commit_at"] is None or state["pending"] or state["speech_open"]:
            return
        if time.monotonic() - state["commit_at"] >= COMMIT_GRACE_SEC:
            done.set()


def start_streaming_session(language_code: str | None = None, is_stale=None) -> StreamingSession:
    """
    language_code=None: Prisma gets the default hint list (hi-IN,en-IN,te-IN)
    and may pick any of them. A specific code (e.g. "hi-IN") locks the session
    to that language for the rest of the call.
    is_stale: polled while waiting for a free session slot; True abandons the
    wait at once (same contract as stt_sarvam.py).
    """
    return StreamingSession(language_code, is_stale)
