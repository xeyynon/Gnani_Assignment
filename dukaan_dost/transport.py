"""
transport.py

Where a call's audio comes from and goes to (DEC-029). The pipeline in
dukaan_dost/app.py (VAD, STT, LLM, TTS, barge-in) is the same whatever
carries the call; only these few operations differ:

    find_nodes()      is a call up right now? Returns (capture key, playback
                      key), both None when there's no call. A NEW key means
                      a new call, even from the same caller (the watchdog
                      compares the capture key every poll).
    device_name()     a label for the log.
    cut_echo_links()  per-poll housekeeping for transports that need it.
    open_capture(k)   a Capture: read_frame(size, timeout) / close().
    play(k, wav, t)   play one WAV clip, blocking, interruptible. Raises
                      PlaybackTimeout if it can't finish within t seconds.
    stop_playback()   end any in-flight clip. True if one was stopped.

Audio is 16 kHz, mono, signed 16-bit little-endian PCM on the capture
side and a WAV file on the playback side (dukaan_dost.app.SAMPLE_RATE).
A transport carrying a different rate converts at its own edge.

Pick one with AUDIO_TRANSPORT (default "pipewire", the Raspberry Pi and
Bluetooth phone this project started on).
"""

import os


class PlaybackTimeout(Exception):
    """play() could not finish within its time limit and gave up."""


class Capture:
    """One call's incoming audio."""

    def read_frame(self, size: int, timeout_sec: float) -> bytes:
        """
        Exactly `size` bytes of audio, bounded by `timeout_sec`. Fewer
        bytes (possibly none) means the stream stalled or ended, and the
        recorder reopens it.
        """
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class Transport:
    name = "base"
    sample_rate = 16000

    # Silence after a clip before the mic is trusted again. A transport
    # whose far end already cancels the agent's own echo can set 0; the
    # ECHO_TAIL_SEC env var overrides it either way.
    default_echo_tail_sec = 0.0

    # True if cut_echo_links() must run on a fast cadence, not just once
    # per watchdog poll (the Bluetooth/PipeWire loopback).
    needs_echo_link_guard = False

    def find_nodes(self) -> tuple:
        raise NotImplementedError

    def device_name(self) -> str:
        return "unknown"

    def cut_echo_links(self) -> None:
        pass

    def open_capture(self, node: str) -> Capture:
        raise NotImplementedError

    def play(self, node: str, wav_bytes: bytes, timeout_sec: float) -> None:
        raise NotImplementedError

    def stop_playback(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        """Release anything the transport holds (sockets, servers)."""


def create(name: str | None = None) -> Transport:
    name = (name or os.environ.get("AUDIO_TRANSPORT", "pipewire")).strip().lower()
    if name == "pipewire":
        from .transport_pipewire import PipewireTransport
        return PipewireTransport()
    raise ValueError(f"AUDIO_TRANSPORT={name!r} is not a known transport (expected 'pipewire')")
