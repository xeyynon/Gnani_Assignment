"""
tts_gnani.py

Gnani Timbre text-to-speech over the realtime WebSocket. Exposes the same
four functions tts_google.py does, so TTS_PROVIDER=gnani (see tts_provider.py)
is a drop-in switch:

    synthesize(text, language_code) -> WAV bytes (16 kHz mono s16) | None
    start_streaming_synthesis(text, language_code) -> object with .chunks()
        (raw 16 kHz mono s16 PCM) and .failed
    needs_digit_spelling(text) -> bool
    warmup()

Protocol, read from docs.gnani.ai/api/TTS/tts-websocket.md on 2026-11-02:
  - wss://api.vachana.ai/api/v1/tts, header X-API-Key-ID.
  - One JSON request {text, voice, model, language, speed, audio_config}.
  - Server: start, then audio messages (data.audio is base64, data.chunk_index,
    data.is_final=false), then complete (is_final=true, no audio), or error.
  - Send one request at a time. Each synthesis here gets its own connection, so
    two sentences can be in flight without sharing a socket.
  - Numbers, dates and currency should be written as spoken words (the docs
    say raw digit strings can be mispronounced); see normalize_text().

NOT YET RUN AGAINST THE REAL SERVICE: no Gnani key was available when this was
written. tests/test_tts_gnani.py runs it against a local stand-in server that
follows the documented protocol. scripts/gnani_smoke_test.py measures the real
time to first chunk and listens to Hindi, Telugu and Hinglish.
"""

import asyncio
import base64
import io
import json
import logging
import os
import queue
import re
import threading
import time
import wave

from .retry import with_retry

log = logging.getLogger("tts_gnani")

SAMPLE_RATE = 16000
REQUEST_TIMEOUT_SEC = float(os.getenv("GNANI_TTS_TIMEOUT_SEC", "20"))
CONNECT_TIMEOUT_SEC = float(os.getenv("GNANI_TTS_CONNECT_TIMEOUT_SEC", "10"))
DEFAULT_LANGUAGE = "en-IN"

# Timbre v3.0 voices each cover all ten languages, so one voice serves every call.
VOICE = os.getenv("GNANI_TTS_VOICE", "Shivani")
MODEL = os.getenv("GNANI_TTS_MODEL", "timbre-v3.0")
SPEED = float(os.getenv("GNANI_TTS_SPEED", "1.0"))        # documented range 0.85 to 1.15

_SUPPORTED = {"hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "bn-IN", "gu-IN"}


def _url() -> str:
    return os.getenv("GNANI_TTS_URL", "wss://api.vachana.ai/api/v1/tts")


def _api_key() -> str:
    key = os.environ.get("GNANI_API_KEY", "")
    if not key:
        raise RuntimeError("GNANI_API_KEY is not set. Get a key at https://app.gnani.ai/voice.")
    return key


def _normalize_language(language_code: str | None) -> str:
    override = os.getenv("GNANI_TTS_LANGUAGE")      # e.g. hi-en to force Hinglish everywhere
    if override:
        return override
    if not language_code:
        return DEFAULT_LANGUAGE
    if language_code.lower() == "hi-en":             # Timbre's Hinglish mode
        return "hi-en"
    code = language_code.replace("_", "-")
    lang, _, region = code.partition("-")
    code = f"{lang.lower()}-{(region or 'IN').upper()}"
    return code if code in _SUPPORTED else DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Text for speech
# ---------------------------------------------------------------------------

_COMMA_NUMBER = re.compile(r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?")
_RUPEE_AFTER = re.compile(r"(?:₹|\bRs\.?|\bINR)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """
    Small, deterministic clean-up before speech: 1,25,000 -> 125000 (so the
    number is one token) and the rupee sign or 'Rs.' in front of an amount
    becomes the word after it ('₹45' -> '45 rupees'). Digits are otherwise left
    to Timbre v3.0. Spelling every number out as words in Hindi and Telugu is
    NOT done here; whether Timbre reads digits well in those languages is
    experiment E2 and decides if it is needed.
    """
    text = _COMMA_NUMBER.sub(lambda m: m.group(0).replace(",", ""), text)
    text = _RUPEE_AFTER.sub(lambda m: f"{m.group(1).replace(',', '')} rupees", text)
    return " ".join(text.split())


def needs_digit_spelling(text: str) -> bool:
    """tts_google.py needed a slower blocking path to read long digit runs digit
    by digit. Timbre has no such special path, so streaming is always used."""
    return False


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

def _request_payload(text: str, language_code: str) -> dict:
    return {
        "text": normalize_text(text),
        "voice": VOICE,
        "model": MODEL,
        "language": _normalize_language(language_code),
        "speed": SPEED,
        "audio_config": {
            "sample_rate": SAMPLE_RATE,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "raw",
        },
    }


class StreamingSynthesis:
    """
    Runs one synthesis in a daemon thread and exposes raw 16 kHz mono s16 PCM
    through chunks() as it arrives. chunks() ends at the end of the stream OR
    on failure; check .failed afterwards to tell the two apart.
    """

    def __init__(self, text: str, language_code: str):
        self._queue: queue.Queue = queue.Queue()
        self._error = None
        self.first_chunk_ms = None            # time from request to the first audio, for measurement
        self.n_chunks = 0
        self._thread = threading.Thread(target=self._run, args=(text, language_code), daemon=True,
                                        name="tts-gnani")
        self._thread.start()

    def chunks(self):
        while True:
            chunk = self._queue.get()
            if chunk is None:
                return
            yield chunk

    @property
    def failed(self) -> bool:
        return self._error is not None

    def _run(self, text: str, language_code: str):
        # The sentinel must go out whatever happens, or a consumer blocked in
        # chunks() hangs forever (the same lesson as tts_google.py).
        try:
            asyncio.run(asyncio.wait_for(self._stream(text, language_code), timeout=REQUEST_TIMEOUT_SEC))
        except asyncio.TimeoutError:
            self._error = f"timed out after {REQUEST_TIMEOUT_SEC:g}s"
            log.error(f"[TTS-GNANI] {self._error}")
        except Exception as e:
            self._error = str(e) or type(e).__name__
            log.error(f"[TTS-GNANI] {self._error}")
        finally:
            self._queue.put(None)

    async def _stream(self, text: str, language_code: str):
        from websockets.asyncio.client import connect

        if not text or not text.strip():
            return
        t0 = time.monotonic()
        headers = {"X-API-Key-ID": _api_key(), "Content-Type": "application/json"}
        ws = await asyncio.wait_for(connect(_url(), additional_headers=headers, max_size=None),
                                    timeout=CONNECT_TIMEOUT_SEC)
        leftover = b""                        # a chunk may end mid-sample; carry the odd byte over
        try:
            await ws.send(json.dumps(_request_payload(text, language_code), ensure_ascii=False))
            async for raw in ws:
                msg = json.loads(raw)
                kind = msg.get("type")
                if kind == "audio":
                    b64 = (msg.get("data") or {}).get("audio") or ""
                    if not b64:
                        continue
                    pcm = leftover + base64.b64decode(b64)
                    if len(pcm) % 2:
                        pcm, leftover = pcm[:-1], pcm[-1:]
                    else:
                        leftover = b""
                    if pcm:
                        if self.first_chunk_ms is None:
                            self.first_chunk_ms = (time.monotonic() - t0) * 1000
                        self.n_chunks += 1
                        self._queue.put(pcm)
                elif kind == "complete":
                    return
                elif kind == "error":
                    raise RuntimeError(msg.get("message") or "error from the speech service")
            raise RuntimeError("connection closed before the synthesis completed")
        finally:
            try:
                await ws.close()
            except Exception:
                pass


def start_streaming_synthesis(text: str, language_code: str) -> StreamingSynthesis:
    return StreamingSynthesis(text, language_code)


# ---------------------------------------------------------------------------
# Whole-clip synthesis and warm-up
# ---------------------------------------------------------------------------

def _pcm_to_wav(pcm: bytes) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return out.getvalue()


def synthesize(text: str, language_code: str = DEFAULT_LANGUAGE) -> bytes | None:
    """The whole clip as 16 kHz mono s16 WAV, or None on failure. Uses the same
    WebSocket path as streaming (the documented realtime endpoint) and retries once."""
    def attempt() -> bytes:
        stream = StreamingSynthesis(text, language_code)
        pcm = b"".join(stream.chunks())
        if stream.failed:
            raise RuntimeError(stream._error)
        if not pcm:
            raise RuntimeError("no audio came back")
        return pcm

    try:
        t0 = time.time()
        pcm = with_retry(attempt)
        log.info(f"[TTS-GNANI] ({_normalize_language(language_code)}, {time.time() - t0:.2f}s)")
        return _pcm_to_wav(pcm)
    except Exception as e:
        log.error(f"[TTS-GNANI] synthesis failed: {e}")
        return None


def warmup():
    """Checks the key is present, then makes one short real synthesis so the
    first caller does not pay the cold connection. A failed synthesis is logged,
    not raised: the process can still start and report the problem on the first call."""
    _api_key()
    t0 = time.time()
    wav = synthesize("Namaste", "en-IN")
    if wav:
        log.info(f"[TTS-GNANI] Warm-up OK, voice={VOICE} model={MODEL} ({time.time() - t0:.2f}s).")
    else:
        log.warning("[TTS-GNANI] Warm-up synthesis failed; check GNANI_API_KEY and the network.")
