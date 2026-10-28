"""
transport.py

Where a call's audio comes from and goes to (DEC-029, DEC-032). The pipeline
in app.py (VAD, STT, LLM, TTS, barge-in) is the same whatever carries the
call; only these few operations differ:

    start()           begin listening for calls (a server, a device).
    find_call()       is a call up right now? Returns (capture key, playback
                      key), both None when there is no call. A NEW key means
                      a new call, even from the same caller (the watchdog
                      compares the capture key every poll).
    device_name()     a label for the log.
    open_capture(k)   a Capture: read_frame(size, timeout) / close().
    play(k, wav, t)   play one WAV clip, blocking, interruptible. Raises
                      PlaybackTimeout if it can't finish within t seconds.
    stop_playback()   end any in-flight clip. True if one was stopped.
    close()           release whatever start() acquired.

Audio is 16 kHz, mono, signed 16-bit little-endian PCM on the capture side
and a WAV file on the playback side (app.SAMPLE_RATE). A transport carrying a
different rate converts at its own edge.

Pick one with AUDIO_TRANSPORT (default "websocket": a call page in a browser).
"""

import os


class PlaybackTimeout(Exception):
    """play() could not finish within its time limit and gave up."""


class Capture:
    """One call's incoming audio."""

    def read_frame(self, size: int, timeout_sec: float) -> bytes:
        """
        Exactly `size` bytes of audio, bounded by `timeout_sec`. Fewer bytes
        (possibly none) means the stream stalled or ended, and the recorder
        reopens it.
        """
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class Transport:
    name = "base"
    sample_rate = 16000

    # How often the watchdog asks find_call() whether a call is up.
    poll_interval_sec = 0.25

    # Silence after a clip before the mic is trusted again. A transport whose
    # far end already cancels the agent's own echo uses 0; the ECHO_TAIL_SEC
    # env var overrides it either way.
    default_echo_tail_sec = 0.0

    # Pause between a call being detected and the greeting starting.
    default_greeting_delay_sec = 0.3

    def start(self) -> None:
        """Begin listening for calls. Called once from main()."""

    def describe(self) -> str:
        """One line telling the operator how to place a call."""
        return self.name

    def find_call(self) -> tuple:
        raise NotImplementedError

    def device_name(self) -> str:
        return "unknown"

    def open_capture(self, key: str) -> Capture:
        raise NotImplementedError

    def play(self, key: str, wav_bytes: bytes, timeout_sec: float) -> None:
        raise NotImplementedError

    def stop_playback(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        """Release anything the transport holds (sockets, servers)."""


def create(name: str | None = None) -> Transport:
    name = (name or os.environ.get("AUDIO_TRANSPORT", "websocket")).strip().lower()
    if name == "websocket":
        from .transport_websocket import WebSocketTransport
        return WebSocketTransport()
    raise ValueError(f"AUDIO_TRANSPORT={name!r} is not a known transport (expected 'websocket')")
