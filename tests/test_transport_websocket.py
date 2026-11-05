"""
Offline tests for the browser (WebSocket) transport (DEC-032).

A real server runs on a free localhost port and a plain WebSocket client plays
the part of the call page, so the protocol is exercised end to end: the page is
served, audio flows in, clips go out, and the page confirms or is told to stop.
No browser, microphone or network is involved.

    python -m pytest tests/test_transport_websocket.py
"""

import io
import json
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import pytest
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost.transport import PlaybackTimeout  # noqa: E402
from dukaan_dost.transport_websocket import WebSocketTransport  # noqa: E402


def make_wav(seconds=0.2, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def wait_for(predicate, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def server():
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.start()
    yield t
    t.close()


@pytest.fixture
def caller(server):
    """A connected 'browser' that has received the ready message."""
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        assert json.loads(ws.recv(timeout=3))["type"] == "ready"
        assert wait_for(lambda: server.find_call()[0] is not None)
        yield ws


def http_get(server, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}{path}", timeout=3) as r:
            return r.status, r.headers, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


# ---- the page --------------------------------------------------------------

def test_the_call_page_is_served_as_html(server):
    status, headers, body = http_get(server, "/")
    assert status == 200
    assert headers.get_all("Content-Type") == ["text/html; charset=utf-8"]
    assert "Start call" in body and "makeResampler" in body


def test_unknown_paths_are_404(server):
    assert http_get(server, "/nope")[0] == 404


def test_the_port_in_use_gives_a_clear_error(server):
    other = WebSocketTransport(host="127.0.0.1", port=server.port)
    with pytest.raises(RuntimeError, match="AUDIO_PORT"):
        other.start()


# ---- call detection --------------------------------------------------------

def test_no_call_until_a_page_connects(server):
    assert server.find_call() == (None, None)


def test_a_connected_page_is_a_call_and_hanging_up_ends_it(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
        key, same = server.find_call()
        assert key == same and key.startswith("web-")
    assert wait_for(lambda: server.find_call() == (None, None))


def test_a_new_connection_gets_a_new_key(server):
    keys = []
    for _ in range(2):
        with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
            ws.recv(timeout=3)
            assert wait_for(lambda: server.find_call()[0] is not None)
            keys.append(server.find_call()[0])
        assert wait_for(lambda: server.find_call() == (None, None))
    assert keys[0] != keys[1]


def test_a_second_caller_is_told_the_line_is_busy(server, caller):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as second:
        assert json.loads(second.recv(timeout=3))["type"] == "busy"


# ---- audio in --------------------------------------------------------------

def test_audio_from_the_page_is_read_back_in_exact_frames(server, caller):
    key = server.find_call()[0]
    cap = server.open_capture(key)
    caller.send(b"ab" * 100)                       # 200 bytes, sent as one message
    caller.send(b"cd" * 100)
    assert cap.read_frame(300, 3) == b"ab" * 100 + b"cd" * 50
    assert cap.read_frame(100, 3) == b"cd" * 50


def test_a_stalled_page_gives_a_short_read_not_a_hang(server, caller):
    cap = server.open_capture(server.find_call()[0])
    t0 = time.monotonic()
    assert cap.read_frame(960, 0.2) == b""
    assert time.monotonic() - t0 < 1.5


def test_hanging_up_ends_the_stream_with_a_short_read(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
        cap = server.open_capture(server.find_call()[0])
        ws.send(b"x" * 10)
        assert wait_for(lambda: True)
    t0 = time.monotonic()
    data = cap.read_frame(960, 3)
    assert len(data) < 960
    assert time.monotonic() - t0 < 2.0             # returned on hang-up, not after the timeout


def test_unread_audio_is_capped_not_unbounded(server, caller):
    key = server.find_call()[0]
    for _ in range(40):
        caller.send(b"\x01" * 32000)               # 1 s each; 40 s in total
    cap = server.open_capture(key)
    time.sleep(0.3)
    total = 0
    while True:
        chunk = cap.read_frame(32000, 0.05)
        if not chunk:
            break
        total += len(chunk)
    assert total <= 16000 * 2 * 10


# ---- audio out -------------------------------------------------------------

def test_a_clip_reaches_the_page_and_play_returns_when_it_confirms(server, caller):
    key = server.find_call()[0]
    wav = make_wav()
    done = []
    t = threading.Thread(target=lambda: (server.play(key, wav, 10), done.append(True)))
    t.start()
    msg = caller.recv(timeout=3)
    clip_id = struct.unpack(">I", msg[:4])[0]
    assert msg[4:] == wav
    assert not done                                 # still waiting for the page
    caller.send(json.dumps({"type": "played", "id": clip_id}))
    t.join(timeout=3)
    assert done == [True]


def test_play_times_out_if_the_page_never_confirms(server, caller):
    key = server.find_call()[0]
    with pytest.raises(PlaybackTimeout):
        server.play(key, make_wav(0.05), 0.3)


def test_stop_playback_tells_the_page_and_releases_play(server, caller):
    key = server.find_call()[0]
    done = []
    t = threading.Thread(target=lambda: (server.play(key, make_wav(2.0), 10), done.append(True)))
    t.start()
    caller.recv(timeout=3)                          # the clip
    assert wait_for(lambda: server.stop_playback() or False, 3)
    assert json.loads(caller.recv(timeout=3))["type"] == "stop"
    t.join(timeout=3)
    assert done == [True]
    assert server.stop_playback() is False          # nothing left in flight


def test_hanging_up_during_a_clip_releases_play(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
        key = server.find_call()[0]
        done = []
        t = threading.Thread(target=lambda: (server.play(key, make_wav(2.0), 10), done.append(True)))
        t.start()
        ws.recv(timeout=3)
    t.join(timeout=3)
    assert done == [True]


def test_playing_to_a_call_that_has_gone_is_a_quiet_no_op(server):
    server.play("web-gone", make_wav(), 1)           # must not raise or block
    assert server.stop_playback() is False


# ---- the real recorder thread over a real socket ---------------------------

def test_the_real_recorder_consumes_audio_sent_by_the_page(server, caller, monkeypatch):
    try:
        import dukaan_dost.app as app
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    key = server.find_call()[0]
    monkeypatch.setattr(app, "_transport", server)
    monkeypatch.setattr(app, "_capture_key", key)
    monkeypatch.setattr(app, "_playback_key", key)
    app._shutdown.clear()
    try:
        t = threading.Thread(target=app.recorder_thread, daemon=True)
        t.start()
        for _ in range(20):
            caller.send(b"\x00" * app.FRAME_BYTES)   # silence, one frame per message
        session = server._session
        assert wait_for(lambda: len(session._buf) == 0), "the recorder did not read the audio"
        app._shutdown.set()
        t.join(timeout=10)
        assert not t.is_alive()
    finally:
        app._shutdown.clear()


# ---- events for the page's live transcript ---------------------------------
def test_an_event_reaches_the_page_as_json(server, caller):
    server.send_event({"type": "user", "text": "ek kilo chawal", "lang": "hi-IN"})
    assert json.loads(caller.recv(timeout=3)) == {"type": "user", "text": "ek kilo chawal", "lang": "hi-IN"}
    server.send_event({"type": "agent", "reply": 3, "text": "Theek hai."})
    assert json.loads(caller.recv(timeout=3))["reply"] == 3


def test_events_keep_their_order(server, caller):
    for n in range(5):
        server.send_event({"type": "agent", "reply": n, "text": str(n)})
    assert [json.loads(caller.recv(timeout=3))["reply"] for _ in range(5)] == [0, 1, 2, 3, 4]


def test_an_event_with_no_call_is_a_quiet_no_op(server):
    server.send_event({"type": "user", "text": "nobody is listening"})   # must not raise or block


def test_an_event_to_a_call_that_has_gone_is_a_quiet_no_op(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
    assert wait_for(lambda: server.find_call()[0] is None)
    server.send_event({"type": "user", "text": "too late"})


def test_a_json_frame_that_is_not_an_object_does_not_end_the_call(server, caller):
    for frame in ("123", "[]", '"played"', "null", "true"):
        caller.send(frame)
    time.sleep(0.2)
    assert server.find_call()[0] is not None                 # still a call
    server.send_event({"type": "agent", "reply": 1, "text": "still here"})
    assert json.loads(caller.recv(timeout=3))["text"] == "still here"
