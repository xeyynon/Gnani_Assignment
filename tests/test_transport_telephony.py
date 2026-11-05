"""
Offline tests for the phone transport (DEC-046).

No Twilio or Exotel account exists yet (KYC, B-39), so a stand-in provider follows the documented messages over a real
local WebSocket: connected, start (with custom parameters), media, mark, stop. This proves our side of the protocol,
not the provider's behaviour.

    python -m pytest tests/test_transport_telephony.py
"""

import base64
import io
import json
import logging
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import transport  # noqa: E402
from dukaan_dost.transport_telephony import (  # noqa: E402
    ExotelAdapter, TelephonyTransport, TwilioAdapter, mulaw_decode, mulaw_encode, resample, _token_ok,
)

TOKEN = "test-only-secret-for-the-stand-in"
PHONE = "+910000000000"            # made up; the test checks it never reaches a log


def make_wav(seconds=0.5, rate=16000, amplitude=3000):
    t = np.arange(int(rate * seconds)) / rate
    pcm = (amplitude * np.sin(2 * np.pi * 440 * t)).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
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
    t = TelephonyTransport(host="127.0.0.1", port=0, token=TOKEN)
    t.configure(default_shop="dukaan_dost", shop_exists=lambda n: n in ("dukaan_dost", "other_shop"))
    t.start()
    yield t
    t.close()


def twilio_url(server):
    return f"ws://127.0.0.1:{server.port}/telephony/twilio"


def exotel_url(server, query=""):
    return f"ws://127.0.0.1:{server.port}/telephony/exotel{query}"


def twilio_start(ws, token=TOKEN, shop=None, sid="MZ1"):
    params = {"token": token}
    if shop:
        params["shop"] = shop
    ws.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
    ws.send(json.dumps({"event": "start", "sequenceNumber": "1", "streamSid": sid,
                        "start": {"streamSid": sid, "accountSid": "AC1", "callSid": "CA1", "from": PHONE,
                                  "tracks": ["inbound"], "customParameters": params,
                                  "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}}))


def exotel_start(ws, token=TOKEN, shop=None, sid="ex1", rate=16000):
    params = {"token": token}
    if shop:
        params["shop"] = shop
    ws.send(json.dumps({"event": "connected"}))
    ws.send(json.dumps({"event": "start", "stream_sid": sid,
                        "start": {"stream_sid": sid, "call_sid": "c1", "from": PHONE, "custom_parameters": params,
                                  "media_format": {"encoding": "raw/slin", "sample_rate": str(rate), "bit_rate": "128kbps"}}}))


def twilio_media(pcm16k_or_8k: np.ndarray) -> str:
    return json.dumps({"event": "media", "streamSid": "MZ1",
                       "media": {"track": "inbound", "payload": base64.b64encode(mulaw_encode(pcm16k_or_8k)).decode()}})


def call_up(server):
    assert wait_for(lambda: server.find_call()[0] is not None)
    return server.find_call()[0]


def played_in_thread(server, key, wav, timeout=4.0):
    box = {}

    def run():
        try:
            server.play(key, wav, timeout)
            box["ok"] = True
        except Exception as e:
            box["error"] = e

    th = threading.Thread(target=run)
    th.start()
    return th, box


# ---- the codec --------------------------------------------------------------

def test_mulaw_round_trip_stays_close():
    t = np.arange(800) / 8000
    pcm = (8000 * np.sin(2 * np.pi * 300 * t)).astype(np.int16)
    back = mulaw_decode(mulaw_encode(pcm))
    assert len(back) == len(pcm)
    assert np.max(np.abs(back.astype(int) - pcm.astype(int))) < 400          # mu-law error is under about 4% of level


def test_mulaw_known_values():
    assert mulaw_encode(np.array([0], dtype=np.int16)) == b"\xff"
    assert mulaw_decode(b"\xff")[0] == 0
    assert mulaw_encode(np.array([32767, -32768], dtype=np.int16)) == b"\x80\x00"


def test_resample_changes_length_by_the_rate_ratio():
    x = np.zeros(1600, dtype=np.int16)
    assert len(resample(x, 16000, 8000)) == 800
    assert len(resample(x[:800], 8000, 16000)) == 1600
    assert len(resample(x, 16000, 16000)) == 1600
    assert len(resample(x[:0], 8000, 16000)) == 0
    assert len(resample(np.zeros(2400, dtype=np.int16), 24000, 16000)) == 1600


def test_a_tone_survives_the_trip_to_the_phone_and_back():
    t = np.arange(16000) / 16000
    tone = (6000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    out = TwilioAdapter().media_out("s", tone.tobytes())
    data = b"".join(base64.b64decode(json.loads(m)["media"]["payload"]) for m in out)
    back = resample(mulaw_decode(data), 8000, 16000)
    spectrum = np.abs(np.fft.rfft(back.astype(float)))
    assert abs(np.argmax(spectrum) * 16000 / len(back) - 440) < 5


# ---- the adapters -----------------------------------------------------------

def test_twilio_ignores_outbound_track_and_junk():
    a = TwilioAdapter()
    assert a.parse("not json") is None
    assert a.parse(json.dumps([1])) is None
    assert a.parse(json.dumps({"event": "media", "media": {"track": "outbound", "payload": "AAAA"}})) is None
    assert a.parse(json.dumps({"event": "weird"})) is None


def test_exotel_chunks_are_multiples_of_320_and_at_least_3200_bytes():
    for rate in (8000, 16000, 24000):
        a = ExotelAdapter(rate)
        for seconds in (0.01, 0.3, 1.234, 2.9):
            pcm = make_wav(seconds)[44:]
            for m in a.media_out("s", pcm):
                size = len(base64.b64decode(json.loads(m)["media"]["payload"]))
                assert size % 320 == 0 and 3200 <= size <= 100000, (rate, seconds, size)


def test_exotel_takes_its_sample_rate_from_the_start_message():
    a = ExotelAdapter(16000)
    a.parse(json.dumps({"event": "start", "stream_sid": "x", "start": {"media_format": {"sample_rate": "8000"}}}))
    assert a.sample_rate == 8000
    pcm8k = np.zeros(160, dtype=np.int16).tobytes()
    ev = a.parse(json.dumps({"event": "media", "stream_sid": "x", "media": {"payload": base64.b64encode(pcm8k).decode()}}))
    assert len(ev.pcm) == 640                               # 160 samples at 8 kHz become 320 samples (640 bytes) at 16 kHz


# ---- the token ---------------------------------------------------------------

def test_token_check_fails_closed():
    assert _token_ok(TOKEN, TOKEN)
    assert not _token_ok("", TOKEN)
    assert not _token_ok("wrong", TOKEN)
    assert not _token_ok("short", "short")                 # a secret under 16 characters is never accepted
    assert not _token_ok("", "")


def closed_with(ws, code):
    with pytest.raises(Exception) as e:
        ws.recv(timeout=3)
    return getattr(e.value, "rcvd", None) is not None and e.value.rcvd.code == code


def test_a_call_without_the_token_is_refused_and_is_not_a_call(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws, token="")
        assert closed_with(ws, 1008)
    assert server.find_call() == (None, None)


def test_a_call_with_the_wrong_token_is_refused(server):
    with connect(exotel_url(server)) as ws:
        exotel_start(ws, token="x" * 30)
        assert closed_with(ws, 1008)
    assert server.find_call() == (None, None)


def test_with_no_secret_configured_every_call_is_refused():
    t = TelephonyTransport(host="127.0.0.1", port=0, token="")
    t.start()
    try:
        with connect(f"ws://127.0.0.1:{t.port}/telephony/twilio") as ws:
            twilio_start(ws, token="")
            assert closed_with(ws, 1008)
    finally:
        t.close()


def test_the_token_may_come_in_the_url_for_a_provider_that_allows_it(server):
    with connect(twilio_url(server) + f"?token={TOKEN}") as ws:
        twilio_start(ws, token="")
        key = call_up(server)
        assert key.startswith("phone-")


def test_an_unknown_shop_is_refused(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws, shop="no_such_shop")
        assert closed_with(ws, 1008)
    assert server.find_call() == (None, None)


def test_a_shop_name_that_is_not_valid_is_refused(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws, shop="../etc")
        assert closed_with(ws, 1008)


def test_the_shop_comes_from_the_start_message(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws, shop="other_shop")
        call_up(server)
        assert server.live_calls()[0]["shop"] == "other_shop"


# ---- one call ---------------------------------------------------------------

def test_a_twilio_call_is_a_call_and_hanging_up_ends_it(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        key = call_up(server)
        assert key.startswith("phone-")
    assert wait_for(lambda: server.find_call() == (None, None))


def test_the_stop_event_ends_the_call(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        call_up(server)
        ws.send(json.dumps({"event": "stop", "streamSid": "MZ1"}))
        assert wait_for(lambda: server.find_call() == (None, None))


def test_caller_audio_arrives_at_16k_in_the_pipeline(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        key = call_up(server)
        cap = server.open_capture(key)
        tone8k = (5000 * np.sin(2 * np.pi * 300 * np.arange(800) / 8000)).astype(np.int16)
        ws.send(twilio_media(tone8k))
        got = cap.read_frame(3200, 3.0)                     # 100 ms at 16 kHz is 3200 bytes; 100 ms at 8 kHz is 800 samples
        assert len(got) == 3200
        samples = np.frombuffer(got, dtype=np.int16)
        assert np.abs(samples).max() > 3000


def test_exotel_audio_at_8k_is_upsampled(server):
    with connect(exotel_url(server)) as ws:
        exotel_start(ws, rate=8000)
        key = call_up(server)
        cap = server.open_capture(key)
        pcm = (4000 * np.sin(2 * np.pi * 300 * np.arange(800) / 8000)).astype("<i2").tobytes()
        ws.send(json.dumps({"event": "media", "stream_sid": "ex1", "media": {"payload": base64.b64encode(pcm).decode()}}))
        assert len(cap.read_frame(3200, 3.0)) == 3200


def test_a_second_call_is_told_the_line_is_busy(server):
    with connect(twilio_url(server)) as first:
        twilio_start(first)
        key = call_up(server)
        with connect(exotel_url(server)) as second:
            exotel_start(second)
            assert closed_with(second, 1013)
        assert server.find_call()[0] == key                 # the first call is untouched


def test_the_next_call_works_after_the_first_hangs_up(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        first = call_up(server)
    assert wait_for(lambda: server.find_call() == (None, None))
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        assert call_up(server) != first


# ---- audio out, marks and barge-in ---------------------------------------------

def test_a_clip_goes_out_as_media_then_a_mark_and_play_waits_for_the_mark_back(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws, sid="MZ9")
        key = call_up(server)
        th, box = played_in_thread(server, key, make_wav(0.5))
        messages = []
        while True:
            m = json.loads(ws.recv(timeout=3))
            messages.append(m)
            if m["event"] == "mark":
                break
        assert [m["event"] for m in messages[:-1]] == ["media"] * (len(messages) - 1) and len(messages) >= 2
        assert all(m["streamSid"] == "MZ9" for m in messages)
        audio = b"".join(base64.b64decode(m["media"]["payload"]) for m in messages[:-1])
        assert len(audio) == 4000                           # 0.5 s of 8 kHz mu-law
        assert th.is_alive()                                # still waiting for the provider to say it was played
        ws.send(json.dumps({"event": "mark", "streamSid": "MZ9", "mark": {"name": messages[-1]["mark"]["name"]}}))
        th.join(3)
        assert box == {"ok": True}


def test_a_clip_never_confirmed_times_out(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        key = call_up(server)
        th, box = played_in_thread(server, key, make_wav(0.1), timeout=0.4)
        th.join(4)
        assert isinstance(box.get("error"), transport.PlaybackTimeout)


def test_a_mark_with_a_strange_name_is_ignored(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        key = call_up(server)
        th, box = played_in_thread(server, key, make_wav(0.1), timeout=0.6)
        ws.send(json.dumps({"event": "mark", "mark": {"name": "garbage"}}))
        th.join(4)
        assert isinstance(box.get("error"), transport.PlaybackTimeout)


def test_barge_in_sends_clear_and_releases_the_player(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws, sid="MZ7")
        key = call_up(server)
        th, box = played_in_thread(server, key, make_wav(1.0), timeout=6.0)
        while json.loads(ws.recv(timeout=3))["event"] != "mark":
            pass
        assert server.stop_playback() is True
        th.join(3)
        assert box == {"ok": True}
        assert json.loads(ws.recv(timeout=3)) == {"event": "clear", "streamSid": "MZ7"}
        assert server.stop_playback() is False              # nothing left to stop


def test_hanging_up_during_a_clip_releases_the_player(server):
    ws = connect(twilio_url(server))
    twilio_start(ws)
    key = call_up(server)
    th, box = played_in_thread(server, key, make_wav(1.0), timeout=6.0)
    time.sleep(0.2)
    ws.close()
    th.join(3)
    assert not th.is_alive()


def test_exotel_clip_is_sent_in_the_documented_shape(server):
    with connect(exotel_url(server, "?sample-rate=16000")) as ws:
        exotel_start(ws, sid="ex5", rate=16000)
        key = call_up(server)
        th, box = played_in_thread(server, key, make_wav(0.5))
        seen = []
        while True:
            m = json.loads(ws.recv(timeout=3))
            seen.append(m)
            if m["event"] == "mark":
                break
        media = [m for m in seen if m["event"] == "media"]
        assert media and all(m["stream_sid"] == "ex5" for m in seen)
        for m in media:
            size = len(base64.b64decode(m["media"]["payload"]))
            assert size % 320 == 0 and 3200 <= size <= 100000
        ws.send(json.dumps({"event": "mark", "stream_sid": "ex5", "mark": {"name": seen[-1]["mark"]["name"]}}))
        th.join(3)
        assert box == {"ok": True}


# ---- privacy, wiring and the browser ---------------------------------------------

def test_the_callers_number_is_never_logged(server, caplog):
    caplog.set_level(logging.DEBUG)
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        call_up(server)
    assert wait_for(lambda: server.find_call() == (None, None))
    assert PHONE not in caplog.text and "0000000000" not in caplog.text
    assert TOKEN not in caplog.text


def test_the_server_is_created_by_name(monkeypatch):
    monkeypatch.setenv("TELEPHONY_TOKEN", TOKEN)
    t = transport.create("telephony")
    assert isinstance(t, TelephonyTransport) and t.name == "telephony"
    assert t.default_echo_tail_sec == 0.0
    with pytest.raises(ValueError, match="telephony"):
        transport.create("nonsense")


def test_a_browser_can_still_call_the_same_server(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        assert json.loads(ws.recv(timeout=3))["type"] == "ready"
        key = call_up(server)
        assert key.startswith("web-")
        th, box = played_in_thread(server, key, make_wav(0.1))
        data = ws.recv(timeout=3)
        assert isinstance(data, bytes)                      # the browser still gets a WAV clip, not phone messages
        clip_id = int.from_bytes(data[:4], "big")
        ws.send(json.dumps({"type": "played", "id": clip_id}))
        th.join(3)
        assert box == {"ok": True}


def test_every_method_the_app_calls_exists_on_the_telephony_transport():
    for name in ("start", "configure", "add_http_handler", "add_ws_handler", "call_shop", "live_calls", "send_event",
                 "find_call", "open_capture", "play", "stop_playback", "close"):
        assert callable(getattr(TelephonyTransport, name, None)), name


# ---- page events are not for the phone provider -----------------------------------------------

def test_page_events_are_not_sent_to_the_phone_provider(server):
    with connect(twilio_url(server)) as ws:
        twilio_start(ws)
        call_up(server)
        server.send_event({"type": "user", "text": "ek kilo chawal", "lang": "hi-IN"})
        server.send_event({"type": "order", "customer": "Ramesh"})
        with pytest.raises(TimeoutError):
            ws.recv(timeout=0.7)


def test_a_browser_call_on_the_same_server_still_gets_the_events(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        assert json.loads(ws.recv(timeout=3))["type"] == "ready"
        call_up(server)
        server.send_event({"type": "user", "text": "ek kilo chawal", "lang": "hi-IN"})
        assert json.loads(ws.recv(timeout=3))["text"] == "ek kilo chawal"
