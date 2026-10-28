"""
Offline tests for the audio transport seam (DEC-029).

Part 1 checks the Pipewire transport issues exactly the commands the
pipeline always ran. Part 2 runs the REAL recorder, _play and watchdog
helpers from dukaan_dost.app against a fake transport, which proves the
pipeline no longer needs the Pi. Nothing here touches PipeWire, a phone
or the network.

    python -m pytest tests/test_transport.py
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import transport as tp  # noqa: E402
from dukaan_dost import transport_pipewire as pw  # noqa: E402


# ---------------------------------------------------------------------------
# Part 1: PipewireTransport issues the same commands as the original code
# ---------------------------------------------------------------------------

class FakeProc:
    def __init__(self, timeout=False, killed_ok=True):
        self.stdout = object()
        self.stdin = object()
        self._timeout = timeout
        self.killed = False
        self.terminated = False
        self.input = None

    def communicate(self, input=None, timeout=None):
        if self._timeout and not self.killed:
            raise subprocess.TimeoutExpired("pw-play", timeout)
        self.input = input
        return (b"", b"")

    def poll(self):
        return None if not self.killed else 0

    def kill(self):
        self.killed = True

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


@pytest.fixture
def popen(monkeypatch):
    calls = []
    procs = []

    def fake_popen(cmd, **kw):
        calls.append((cmd, kw))
        p = FakeProc()
        procs.append(p)
        return p

    monkeypatch.setattr(pw.subprocess, "Popen", fake_popen)
    return calls, procs


def test_find_nodes_parses_wpctl_output(monkeypatch):
    out = "  bluez_input.AA_BB_CC_DD_EE_FF.1\n  bluez_output.AA_BB_CC_DD_EE_FF.1\n"
    monkeypatch.setattr(pw.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=out))
    assert pw.PipewireTransport().find_nodes() == (
        "bluez_input.AA_BB_CC_DD_EE_FF.1", "bluez_output.AA_BB_CC_DD_EE_FF.1")


def test_find_nodes_with_no_call_or_no_wpctl(monkeypatch):
    monkeypatch.setattr(pw.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="nothing here"))
    assert pw.PipewireTransport().find_nodes() == (None, None)

    def boom(*a, **k):
        raise FileNotFoundError("wpctl")
    monkeypatch.setattr(pw.subprocess, "run", boom)
    assert pw.PipewireTransport().find_nodes() == (None, None)


def test_open_capture_runs_the_original_pw_record_command(popen):
    calls, _ = popen
    pw.PipewireTransport().open_capture("bluez_input.X.1")
    cmd, kw = calls[0]
    assert cmd == ["pw-record", "--target", "bluez_input.X.1", "-",
                   "--rate", "16000", "--channels", "1", "--format", "s16"]
    assert kw["stdout"] == subprocess.PIPE


def test_play_runs_the_original_pw_play_command_and_sends_the_wav(popen):
    calls, procs = popen
    t = pw.PipewireTransport()
    t.play("bluez_output.X.1", b"RIFFwav", 45)
    assert calls[0][0] == ["pw-play", "--target", "bluez_output.X.1", "-"]
    assert procs[0].input == b"RIFFwav"
    assert t.stop_playback() is False       # nothing in flight afterwards


def test_play_timeout_kills_the_process_and_raises(monkeypatch):
    p = FakeProc(timeout=True)
    monkeypatch.setattr(pw.subprocess, "Popen", lambda *a, **k: p)
    with pytest.raises(tp.PlaybackTimeout):
        pw.PipewireTransport().play("n", b"x", 1)
    assert p.killed


def test_stop_playback_kills_an_in_flight_clip(monkeypatch):
    t = pw.PipewireTransport()
    p = FakeProc()
    t._play_proc = p
    assert t.stop_playback() is True
    assert p.killed


def test_capture_close_terminates_the_process():
    p = FakeProc()
    pw.PipewireCapture(p).close()
    assert p.terminated


def test_capture_read_frame_returns_exact_bytes_and_short_reads_on_eof(monkeypatch):
    data = [b"abc", b"def", b""]
    monkeypatch.setattr(pw.select, "select", lambda r, w, x, t: (r, [], []))
    monkeypatch.setattr(pw.os, "read", lambda fd, n: data.pop(0)[:n])
    proc = FakeProc()
    proc.stdout = type("Stdout", (), {"fileno": lambda self: 0})()
    cap = pw.PipewireCapture(proc)
    assert cap.read_frame(6, 1) == b"abcdef"    # two reads joined into one exact frame
    assert cap.read_frame(6, 1) == b""          # EOF: short read, the recorder reopens


def test_pipewire_transport_defaults_match_the_bluetooth_setup():
    t = pw.PipewireTransport()
    assert (t.sample_rate, t.default_echo_tail_sec, t.needs_echo_link_guard) == (16000, 1.2, True)


def test_create_defaults_to_pipewire_and_rejects_unknown_names(monkeypatch):
    monkeypatch.delenv("AUDIO_TRANSPORT", raising=False)
    assert tp.create().name == "pipewire"
    with pytest.raises(ValueError):
        tp.create("carrier-pigeon")


# ---------------------------------------------------------------------------
# Part 2: the real pipeline code against a fake transport
# ---------------------------------------------------------------------------

class FakeCapture(tp.Capture):
    def __init__(self, shutdown, frames_before_stop=5):
        self.reads = []
        self.closed = False
        self._shutdown = shutdown
        self._left = frames_before_stop

    def read_frame(self, size, timeout_sec):
        self.reads.append((size, timeout_sec))
        self._left -= 1
        if self._left <= 0:
            self._shutdown.set()
        return b"\x00" * size            # digital silence

    def close(self):
        self.closed = True


class FakeTransport(tp.Transport):
    name = "fake"
    default_echo_tail_sec = 0.0

    def __init__(self):
        self.nodes = ("fake-in", "fake-out")
        self.played = []
        self.stopped = 0
        self.capture = None
        self.raise_timeout = False
        self.opened_with = None

    def find_nodes(self):
        return self.nodes

    def device_name(self):
        return "fake phone"

    def open_capture(self, node):
        self.opened_with = node
        return self.capture

    def play(self, node, wav_bytes, timeout_sec):
        if self.raise_timeout:
            raise tp.PlaybackTimeout("stalled")
        self.played.append((node, wav_bytes, timeout_sec))

    def stop_playback(self):
        self.stopped += 1
        return True


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("SHOP_NAME", "transport_test")
    try:
        import dukaan_dost.app as m
    except Exception as e:                       # e.g. webrtcvad missing on this machine
        pytest.skip(f"main module not importable here: {e}")
    return m


@pytest.fixture
def fake(app, monkeypatch):
    t = FakeTransport()
    monkeypatch.setattr(app, "_transport", t)
    monkeypatch.setattr(app, "ECHO_TAIL_SEC", 0)
    monkeypatch.setattr(app, "_out_node", "fake-out")
    monkeypatch.setattr(app, "_inp_node", "fake-in")
    app._playing.clear()
    app._shutdown.clear()
    yield t
    app._shutdown.clear()
    app._playing.clear()


def test_main_module_delegates_call_detection_to_the_transport(app, fake):
    assert app._find_nodes() == ("fake-in", "fake-out")
    assert app._device_name() == "fake phone"


def test_play_goes_through_the_transport_and_toggles_playing(app, fake):
    seen = {}

    def spy(node, wav, timeout):
        seen["playing_during"] = app._playing.is_set()
        fake.played.append((node, wav, timeout))
    fake.play = spy

    app._play(b"WAV")
    assert fake.played == [("fake-out", b"WAV", app.PW_PLAY_TIMEOUT_SEC)]
    assert seen["playing_during"] is True
    assert not app._playing.is_set()


def test_play_with_no_output_node_plays_nothing(app, fake, monkeypatch):
    monkeypatch.setattr(app, "_out_node", None)
    app._play(b"WAV")
    assert fake.played == []


def test_play_timeout_is_logged_and_clears_playing(app, fake):
    fake.raise_timeout = True
    app._play(b"WAV")                    # must not raise
    assert not app._playing.is_set()


def test_stop_playback_reaches_the_transport(app, fake):
    app._stop_playback("test")
    assert fake.stopped == 1


def test_recorder_reads_frames_from_the_transport_and_closes_it(app, fake):
    fake.capture = FakeCapture(app._shutdown, frames_before_stop=5)
    t = threading.Thread(target=app.recorder_thread, daemon=True)
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "recorder_thread did not stop"
    assert fake.opened_with == "fake-in"
    assert len(fake.capture.reads) >= 5
    assert all(size == app.FRAME_BYTES for size, _ in fake.capture.reads)
    assert fake.capture.closed


def test_pipeline_sample_rate_is_what_the_pipewire_transport_carries(app):
    assert app.SAMPLE_RATE == pw.PipewireTransport.sample_rate
