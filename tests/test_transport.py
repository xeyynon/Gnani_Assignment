"""
Offline tests for the audio transport seam (DEC-029, DEC-032).

These run the REAL recorder, _play, _stop_playback and call-detection code from
dukaan_dost.app against a fake transport, which proves the pipeline only needs
the Transport interface. The WebSocket transport itself is tested in
test_transport_websocket.py.

    python -m pytest tests/test_transport.py
"""

import os
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import transport as tp  # noqa: E402


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

    def __init__(self):
        self.call = ("fake-in", "fake-out")
        self.played = []
        self.stopped = 0
        self.capture = None
        self.raise_timeout = False
        self.opened_with = None

    def find_call(self):
        return self.call

    def device_name(self):
        return "fake caller"

    def open_capture(self, key):
        self.opened_with = key
        return self.capture

    def play(self, key, wav_bytes, timeout_sec):
        if self.raise_timeout:
            raise tp.PlaybackTimeout("stalled")
        self.played.append((key, wav_bytes, timeout_sec))

    def stop_playback(self):
        self.stopped += 1
        return True


@pytest.fixture(scope="module")
def app():
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
    monkeypatch.setattr(app, "_playback_key", "fake-out")
    monkeypatch.setattr(app, "_capture_key", "fake-in")
    app._playing.clear()
    app._shutdown.clear()
    yield t
    app._shutdown.clear()
    app._playing.clear()


def test_importing_the_app_does_not_open_a_port(app):
    # create() builds the transport but only main() starts it.
    assert getattr(app._transport, "_thread", None) is None


def test_default_transport_is_the_websocket_one(app):
    assert app._transport.name == "websocket" or os.environ.get("AUDIO_TRANSPORT")


def test_unknown_transport_names_are_rejected():
    with pytest.raises(ValueError):
        tp.create("carrier-pigeon")


def test_main_module_delegates_call_detection_to_the_transport(app, fake):
    assert app._find_call() == ("fake-in", "fake-out")
    assert app._device_name() == "fake caller"


def test_play_goes_through_the_transport_and_toggles_playing(app, fake):
    seen = {}

    def spy(key, wav, timeout):
        seen["playing_during"] = app._playing.is_set()
        fake.played.append((key, wav, timeout))
    fake.play = spy

    app._play(b"WAV")
    assert fake.played == [("fake-out", b"WAV", app.PLAY_TIMEOUT_SEC)]
    assert seen["playing_during"] is True
    assert not app._playing.is_set()


def test_play_with_no_playback_key_plays_nothing(app, fake, monkeypatch):
    monkeypatch.setattr(app, "_playback_key", None)
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


def test_pipeline_sample_rate_matches_the_default_transport(app):
    from dukaan_dost.transport_websocket import WebSocketTransport
    assert app.SAMPLE_RATE == WebSocketTransport.sample_rate


def test_no_raspberry_pi_tools_are_left_in_the_code():
    root = Path(__file__).resolve().parent.parent / "dukaan_dost"
    banned = ("pw-record", "pw-play", "wpctl", "pw-link", "bluetoothctl")
    hits = []
    for py in root.glob("*.py"):
        code = [l for l in py.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#")]
        text = "\n".join(code)
        # strings that are not comments or docstring prose: look for them as quoted command parts
        for word in banned:
            if f'"{word}"' in text or f"'{word}'" in text:
                hits.append((py.name, word))
    assert hits == [], f"Raspberry Pi tool calls remain: {hits}"
