"""
transport_replay.py

A "caller" that is a script, so the WHOLE voice loop (voice detection, Prisma, the language model, the
order code, Timbre, barge-in) can run with no browser and no person: AUDIO_TRANSPORT=replay with
REPLAY_PLAN=<plan.json>. It is what the evaluation (evaluation/run_calls.py) runs on.

It plays prepared speech into the real pipeline at real-time pace, as a microphone would, with
silence (or steady background noise) in between, and it plays the agent's replies out in real time
too, so the agent's own timing, including its listening gaps, behaves as on a real call. It records
for every turn: when the caller stopped speaking, when the first audio of the agent's reply began
(time to first audio), what the speech recogniser heard and what the agent said, and, at the end,
writes it all to the plan's results file. There is no echo from the agent's voice back into the
"microphone", and nothing is simulated about the phone line: that is for the real call test.

Plan file (JSON):
    {"results": "C:/.../results.json",            # written as the run goes; "done": true at the end
     "min_turn_sec": 14,                          # least time between the starts of two caller turns
     "quiet_sec": 1.5,                            # agent silent this long = it has finished speaking
     "response_timeout_sec": 25,                  # give up waiting for a reply after this
     "noise": {"path": "noise.wav", "gain": 0.05},# optional steady noise mixed into the microphone all call
     "calls": [{"id": "s01", "shop": "dukaan_dost",
                "turns": [{"audio": "C:/.../s01_t1.wav", "text": "what was said",
                           "barge_in_after_sec": null}]}]}
A turn with barge_in_after_sec speaks that many seconds after the agent's reply began, over the agent,
instead of waiting for it to finish. It does not wait out min_turn_sec first: that gap would let the reply end.

Each turn record carries first_audio_after_ms (from the LAST SAMPLE OF THE CLIP to the first sample of the reply) and
trailing_silence_ms (the quiet at the end of the clip), so the time from the caller's last WORD is the sum of the two.
"""

import json
import logging
import os
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from .transport import Capture, Transport

log = logging.getLogger("transport_replay")

FRAME_BYTES_PER_SEC = 16000 * 2
GREETING_WAIT_SEC = 20.0
END_CALL_WAIT_SEC = 8.0           # how long to let the agent notice the call has ended and save the order
RESULT_WRITE_TRIES = 12            # tries to write the results file; on Windows the replace fails while a reader has the file open


def _wav_pcm(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
            raise ValueError(f"{path}: need 16 kHz mono 16-bit audio")
        return w.readframes(w.getnframes())


def trailing_silence_ms(pcm: bytes, frame_ms: int = 20, rms_below: float = 300.0) -> int:
    """How long the clip is quiet at its end, in ms: whole 20 ms frames counted back from the last sample whose RMS is under
    300. A synthetic voice clip ends with a pause; the caller's last word was spoken before it. The scorer (evaluation/score_calls.py) uses the same function for old results."""
    a = np.frombuffer(pcm[:len(pcm) // 2 * 2], dtype=np.int16).astype(np.float64)
    n = int(16000 * frame_ms / 1000)
    quiet, end = 0, len(a)
    while end >= n and np.sqrt(np.mean(a[end - n:end] ** 2)) < rms_below:
        quiet += 1
        end -= n
    return quiet * frame_ms


def _wav_seconds(wav_bytes: bytes) -> float:
    import io
    try:
        with wave.open(io.BytesIO(wav_bytes)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 5.0


class _ReplayCapture(Capture):
    def __init__(self, transport):
        self._t = transport

    def read_frame(self, size: int, timeout_sec: float) -> bytes:
        return self._t._next_frame(size, timeout_sec)

    def close(self) -> None:
        pass


class ReplayTransport(Transport):
    name = "replay"
    sample_rate = 16000
    poll_interval_sec = 0.1
    default_echo_tail_sec = 0.0
    default_greeting_delay_sec = 0.3

    def __init__(self, plan: dict):
        self.plan = plan
        self.min_turn_sec = float(plan.get("min_turn_sec", 14))
        self.quiet_sec = float(plan.get("quiet_sec", 1.5))
        self.response_timeout_sec = float(plan.get("response_timeout_sec", 25))
        self.results_path = Path(plan["results"]) if plan.get("results") else None
        self._noise = None
        noise = plan.get("noise")
        if noise:
            raw = np.frombuffer(_wav_pcm(noise["path"]), dtype=np.int16).astype(np.float32)
            self._noise = (raw * float(noise.get("gain", 0.05)))
            self._noise_pos = 0

        self._cond = threading.Condition()
        self._inject = bytearray()                 # speech waiting to be "heard"
        self._markers = []                         # (bytes consumed that means the speech is over, record dict)
        self._consumed = 0
        self._due = None                           # when the next microphone frame is due
        self._stop = threading.Event()             # stop_playback
        self._playing = False
        self._plays = []
        self._events = []
        self._calls_out = []
        self._cur = None                           # the call in progress
        self._cur_key = None
        self._call_shop = None
        self._none_polls = 0
        self._t0 = time.monotonic()
        self._done = False
        self._error = None                         # set if the scripted caller crashed
        self._thread = None
        self._closed = False

    @classmethod
    def from_file(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    # ---- the Transport interface -----------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True, name="replay-caller")
            self._thread.start()

    def describe(self) -> str:
        return f"replaying {len(self.plan.get('calls', []))} scripted call(s); results go to {self.results_path}"

    def device_name(self) -> str:
        return "replay"

    def call_shop(self):
        return self._call_shop

    def live_calls(self) -> list:
        return [{"shop": self._call_shop, "seconds": 0}] if self._cur_key else []

    def find_call(self):
        with self._cond:
            if self._cur_key is None:
                self._none_polls += 1
                self._cond.notify_all()
                return None, None
            self._none_polls = 0
            return self._cur_key, self._cur_key

    def open_capture(self, key: str) -> Capture:
        return _ReplayCapture(self)

    def send_event(self, event: dict) -> None:
        with self._cond:
            self._events.append({"t": self._now(), **event})
            self._cond.notify_all()

    def play(self, key: str, wav_bytes: bytes, timeout_sec: float) -> None:
        dur = _wav_seconds(wav_bytes)
        rec = {"t": self._now(), "dur": dur, "stopped": False}
        with self._cond:
            self._plays.append(rec)
            self._playing = True
            self._stop.clear()
            self._cond.notify_all()
        end = time.monotonic() + dur
        while time.monotonic() < end and not self._stop.is_set() and not self._closed:
            time.sleep(0.01)
        with self._cond:
            rec["stopped"] = self._stop.is_set()
            rec["end"] = self._now()
            self._playing = False
            self._cond.notify_all()

    def stop_playback(self) -> bool:
        with self._cond:
            was = self._playing
        self._stop.set()
        return was

    def close(self) -> None:
        self._closed = True
        with self._cond:
            self._cond.notify_all()
        # `_done` is set just BEFORE the last results file is written, so a caller that sees it and reads the file
        # at once races the write (on Windows the reader's open handle makes the replace fail with "Access is
        # denied"). Waiting for the caller thread to finish makes close() return only when the file is written.
        thread = self._thread
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=10.0)

    # ---- the microphone ---------------------------------------------------------------------------------

    def _now(self) -> float:
        return round(time.monotonic() - self._t0, 3)

    def _next_frame(self, size: int, timeout_sec: float) -> bytes:
        dur = size / FRAME_BYTES_PER_SEC
        now = time.monotonic()
        if self._due is None or self._due < now - 0.5:
            self._due = now                          # never burst to catch up
        wait = self._due - now
        if wait > timeout_sec:
            time.sleep(max(0.0, timeout_sec))
            return b""
        if wait > 0:
            time.sleep(wait)
        self._due += dur
        with self._cond:
            chunk = bytes(self._inject[:size])
            del self._inject[:size]
            self._consumed += size
            for marker in list(self._markers):
                if self._consumed >= marker[0]:
                    marker[1]["t_speech_end"] = self._now()
                    self._markers.remove(marker)
                    self._cond.notify_all()
        samples = np.zeros(size // 2, dtype=np.float32)
        if chunk:
            samples[:len(chunk) // 2] = np.frombuffer(chunk, dtype=np.int16)
        if self._noise is not None:
            n = len(samples)
            idx = (self._noise_pos + np.arange(n)) % len(self._noise)
            samples += self._noise[idx]
            self._noise_pos = (self._noise_pos + n) % len(self._noise)
        return np.clip(samples, -32768, 32767).astype(np.int16).tobytes()

    # ---- the scripted caller ------------------------------------------------------------------------------

    def _wait_for(self, predicate, timeout):
        """Blocks until predicate() is true or `timeout` seconds pass. Returns the predicate's value."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while not predicate():
                left = deadline - time.monotonic()
                if left <= 0 or self._closed:
                    return predicate()
                self._cond.wait(min(left, 0.2))
            return True

    def _plays_after(self, t):
        return [p for p in self._plays if p["t"] >= t]

    def _agent_quiet(self) -> bool:
        if self._playing:
            return False
        last = max([p.get("end", p["t"]) for p in self._plays] or [0.0])
        return self._now() - last >= self.quiet_sec

    def _run(self):
        try:
            for call in self.plan.get("calls", []):
                if self._closed:
                    break
                self._one_call(call)
                self._write_results()
        except Exception as e:
            self._error = f"{type(e).__name__}: {e}"
            log.exception("[REPLAY] the scripted caller failed")
        finally:
            self._done = True
            if not self._write_results():                 # a failed write must not leave a file that says done
                log.error("[REPLAY] the final results could not be written")
            log.info("[REPLAY] all scripted calls finished")

    def _one_call(self, call):
        rec = {"id": call["id"], "shop": call.get("shop"), "t_begin": self._now(),
               "begin_iso": datetime.now().astimezone().isoformat(timespec="seconds"), "turns": []}
        self._cur = rec
        self._events_start = len(self._events)
        self._plays_start = len(self._plays)
        with self._cond:
            self._call_shop = call.get("shop")
            self._cur_key = f"replay-{call['id']}"
            self._none_polls = 0
            self._inject.clear()
            self._cond.notify_all()
        log.info(f"[REPLAY] call {call['id']} begins")

        # the agent greets first; wait for it to finish before the caller speaks
        self._wait_for(lambda: len(self._plays) > self._plays_start, GREETING_WAIT_SEC)
        self._wait_for(self._agent_quiet, 30)
        rec["greeting_played"] = len(self._plays) > self._plays_start

        last_turn_start = None
        for i, turn in enumerate(call.get("turns", [])):
            if self._closed:
                break
            barge = turn.get("barge_in_after_sec")
            interrupting = barge is not None and bool(self._plays)
            if last_turn_start is not None and not interrupting:      # an interrupting turn must start while the reply plays
                gap = self.min_turn_sec - (self._now() - last_turn_start)
                if gap > 0:
                    time.sleep(gap)                       # stay under the language model's rate limit
            if interrupting:
                self._wait_for(lambda: self._playing, 5)
                started = self._plays[-1]["t"]            # the barge delay counts from when the reply began, not from now
                wait = started + float(barge) - self._now()
                if wait > 0:
                    time.sleep(wait)
            else:
                self._wait_for(self._agent_quiet, 30)
            pcm = _wav_pcm(turn["audio"])
            t_rec = {"i": i, "audio": turn["audio"], "text": turn.get("text"), "t_start": self._now(),
                     "speech_seconds": round(len(pcm) / FRAME_BYTES_PER_SEC, 2), "trailing_silence_ms": trailing_silence_ms(pcm)}
            rec["turns"].append(t_rec)
            last_turn_start = self._now()
            with self._cond:
                self._inject += pcm
                self._markers.append((self._consumed + len(self._inject), t_rec))
            self._wait_for(lambda: "t_speech_end" in t_rec, len(pcm) / FRAME_BYTES_PER_SEC + 10)
            t_end = t_rec.get("t_speech_end", self._now())
            got = self._wait_for(lambda: bool(self._plays_after(t_end)), self.response_timeout_sec)
            replies = self._plays_after(t_end)
            if got and replies:
                t_rec["first_audio_after_ms"] = round((replies[0]["t"] - t_end) * 1000)
            else:
                t_rec["first_audio_after_ms"] = None
                t_rec["no_response"] = True
            turns = call.get("turns", [])
            next_barges = i + 1 < len(turns) and turns[i + 1].get("barge_in_after_sec") is not None
            if not next_barges:                     # an interrupting next turn must speak while the agent still talks
                self._wait_for(self._agent_quiet, 40)

        # hang up: the agent must notice the call has gone, which saves the order
        self._wait_for(lambda: not self._playing, 30)
        with self._cond:
            self._cur_key = None
            self._cond.notify_all()
        self._wait_for(lambda: self._none_polls >= 8, END_CALL_WAIT_SEC)
        time.sleep(1.0)                                    # the order file is written just after "call ended"
        rec["t_end"] = self._now()
        rec["end_iso"] = datetime.now().astimezone().isoformat(timespec="seconds")
        self._finish_record(rec)
        self._calls_out.append(rec)
        self._cur = None
        log.info(f"[REPLAY] call {call['id']} ended")

    def _finish_record(self, rec):
        events = self._events[self._events_start:]
        plays = self._plays[self._plays_start:]
        starts = [t["t_start"] for t in rec["turns"]] + [rec["t_begin"] + 10 ** 6]
        for k, t in enumerate(rec["turns"]):
            lo, hi = t["t_start"], starts[k + 1]
            t["heard"] = [e["text"] for e in events if e.get("type") == "user" and lo <= e["t"] < hi]
            t["agent_said"] = [e["text"] for e in events if e.get("type") == "agent" and lo <= e["t"] < hi]
            t["agent_played_seconds"] = round(sum(p["dur"] for p in plays if lo <= p["t"] < hi), 2)
        rec["greeting_text"] = [e["text"] for e in events if e.get("type") == "agent" and e["t"] < (starts[0] if rec["turns"] else 1e9)]
        orders = [e for e in events if e.get("type") == "order"]
        rec["last_order_event"] = orders[-1] if orders else None
        rec["interrupted_clips"] = sum(1 for p in plays if p.get("stopped"))

    def _write_results(self) -> bool:
        """Writes the results file through a temp file. On Windows the replace fails while another process has the file open,
        so it is retried; a write that still fails is logged and returns False (the file then keeps its last good content,
        which never says done), and the remaining calls go on."""
        if self.results_path is None:
            return True
        data = {"done": self._done, "aborted": self._error is not None, "error": self._error,
                "written_iso": datetime.now().astimezone().isoformat(timespec="seconds"), "calls": self._calls_out}
        tmp = self.results_path.with_name(self.results_path.name + ".tmp")
        for attempt in range(RESULT_WRITE_TRIES):
            try:
                self.results_path.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                os.replace(tmp, self.results_path)
                return True
            except OSError as e:
                log.warning(f"[REPLAY] writing the results failed (try {attempt + 1}/{RESULT_WRITE_TRIES}): {e}")
                if attempt < RESULT_WRITE_TRIES - 1:
                    time.sleep(min(0.25, 0.02 + 0.02 * attempt))    # 20 ms rising to 250 ms: about 2 seconds in all
        return False
