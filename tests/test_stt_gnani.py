"""
Tests for the Gnani speech-to-text backend, run against a stand-in server that follows the
protocol documented at docs.gnani.ai/api/STT/stt-websocket.md. They show the client does
what the docs say; they cannot show the real service agrees (see scripts/gnani_smoke_test.py).

    python -m pytest tests/test_stt_gnani.py
"""

import importlib
import json
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_ws import FakeServer  # noqa: E402

from dukaan_dost import stt_gnani  # noqa: E402


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-key")
    for name in ("GNANI_STT_LANGUAGES", "GNANI_STT_FORMAT", "GNANI_STT_MODEL", "GNANI_STT_KEYTERMS",
                 "GNANI_STT_MIN_SILENCE_MS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(stt_gnani, "COMMIT_GRACE_SEC", 0.1)
    monkeypatch.setattr(stt_gnani, "STREAMING_FINISH_TIMEOUT_SEC", 3.0)
    monkeypatch.setattr(stt_gnani, "TRAILING_SILENCE_SEC", 0.2)
    monkeypatch.setattr(stt_gnani, "BURST_ALLOWANCE_SEC", 10.0)      # no pacing delay unless a test wants it
    stt_gnani.set_keyterms([])


class Recorder:
    def __init__(self):
        self.headers = None
        self.binary = []
        self.text = []


def speech(n_bytes=1024 * 20):
    return b"\x01\x02" * (n_bytes // 2)


def make_server(rec, on_commit=None, on_silence=None, on_connect=None, silence_frames=3):
    """A stand-in Prisma. on_commit / on_silence are async functions taking the connection."""
    async def handler(ws):
        rec.headers = ws.request.headers
        await ws.send(json.dumps({"type": "connected", "config": {"sample_rate": 16000, "chunk_size": 512}}))
        if on_connect:
            await on_connect(ws)
        quiet, heard = 0, False          # a segment only closes on silence that follows speech
        async for msg in ws:
            if isinstance(msg, bytes):
                rec.binary.append(len(msg))
                if msg == b"\x00" * 1024:
                    quiet += 1
                    if on_silence and heard and quiet == silence_frames:
                        heard = False
                        await on_silence(ws)
                else:
                    quiet, heard = 0, True
            else:
                rec.text.append(msg)
                if json.loads(msg).get("type") == "commit":
                    if on_commit:                      # a server that supports commit closes the open utterance
                        heard = False
                        await on_commit(ws)
    return FakeServer(handler)


async def reply(ws, text, lang="hi-IN", with_processing=True):
    await ws.send(json.dumps({"type": "speech_start", "utterance_id": "u"}))
    if with_processing:
        await ws.send(json.dumps({"type": "processing"}))
    await ws.send(json.dumps({"type": "transcript", "text": text, "is_final": True,
                              "detected_language_code": lang, "segment_index": 1}))


def run(server, language=None, audio=None, is_stale=None, chunk=1500):
    stt_gnani_url = server.url
    import os
    os.environ["GNANI_STT_URL"] = stt_gnani_url
    session = stt_gnani.start_streaming_session(language, is_stale)
    audio = speech() if audio is None else audio
    for i in range(0, len(audio), chunk):
        session.feed(audio[i:i + chunk])
    return session.finish()


# ---- what is sent -----------------------------------------------------------

def test_headers_follow_the_documented_names_in_both_spellings():
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "namaste")

    with make_server(rec, on_commit) as s:
        run(s, language="hi-IN")
    h = rec.headers
    assert h["x-api-key-id"] == "test-key"
    assert h["language_code"] == "hi-IN" and h["lang_code"] == "hi-IN"
    assert h["model"] == "prisma-v3.0" and h["x-model"] == "prisma-v3.0"
    assert h["format"] == "transcribe" and h["x-format"] == "transcribe"
    assert h["x-sample-rate"] == "16000"


def test_no_language_sends_the_hint_list_and_a_locked_language_sends_one_code():
    rec = Recorder()
    with make_server(rec) as s:
        run(s)
    assert rec.headers["language_code"] == "hi-IN,en-IN,te-IN"
    with make_server(rec) as s:
        run(s, language="te-in")
    assert rec.headers["language_code"] == "te-IN"


def test_keyterms_are_sent_but_non_ascii_terms_are_skipped():
    assert stt_gnani.set_keyterms(["Maggi", "Amul butter", "मैगी", "tea, strong", "maggi", ""]) == 2
    rec = Recorder()
    with make_server(rec) as s:
        run(s)
    assert rec.headers["keyterms"] == "Maggi,Amul butter" == rec.headers["x-keyterms"]


def test_every_audio_frame_is_exactly_1024_bytes_and_the_tail_is_padded():
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "hello", "en-IN")

    with make_server(rec, on_commit) as s:
        run(s, audio=speech(1024 * 5 + 300), chunk=777)      # awkward chunk sizes, partial last frame
    assert rec.binary and set(rec.binary) == {1024}
    assert sum(1 for n in rec.binary) >= 6                    # 5 full frames + the padded one (+ silence)


def test_a_commit_frame_is_sent_after_the_audio():
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "hello", "en-IN")

    with make_server(rec, on_commit) as s:
        run(s)
    assert json.loads(rec.text[-1]) == {"type": "commit"}


def test_audio_is_paced_not_sent_in_a_burst(monkeypatch):
    monkeypatch.setattr(stt_gnani, "BURST_ALLOWANCE_SEC", 0.1)
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "ok", "en-IN")

    with make_server(rec, on_commit) as s:
        t0 = time.monotonic()
        run(s, audio=speech(int(16000 * 2 * 0.8)))             # 0.8 s of audio, handed over at once
        elapsed = time.monotonic() - t0
    assert elapsed >= 0.55          # about 0.8 s of audio minus the 0.1 s allowance, not instant


# ---- what comes back --------------------------------------------------------

def test_the_transcript_and_detected_language_come_back():
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "do kilo atta", "hi-IN")

    with make_server(rec, on_commit) as s:
        assert run(s) == ("do kilo atta", "hi-IN")


def test_segments_closed_by_the_server_before_commit_are_joined():
    rec = Recorder()

    async def mid_stream(ws):
        await reply(ws, "do kilo atta", "hi-IN")

    async def on_commit(ws):
        await reply(ws, "aur ek litre oil", "hi-IN")

    with make_server(rec, on_commit, on_silence=mid_stream, silence_frames=1) as s:
        # silence in the audio makes the stand-in close a segment before commit arrives
        audio = speech(1024 * 4) + b"\x00" * 1024 * 3 + speech(1024 * 4)
        text, lang = run(s, audio=audio)
    assert text == "do kilo atta aur ek litre oil" and lang == "hi-IN"


def test_no_speech_gives_an_empty_result_not_an_error():
    rec = Recorder()
    with make_server(rec) as s:                                # never replies
        assert run(s) == ("", "")


def test_a_server_that_ignores_commit_still_finishes_through_trailing_silence(monkeypatch):
    rec = Recorder()

    async def on_silence(ws):
        await reply(ws, "namaste", "hi-IN")

    with make_server(rec, on_commit=None, on_silence=on_silence, silence_frames=3) as s:
        assert run(s) == ("namaste", "hi-IN")


def test_an_error_message_gives_the_error_marker():
    rec = Recorder()

    async def on_commit(ws):
        await ws.send(json.dumps({"type": "error", "message": "RATE_LIMITED"}))

    with make_server(rec, on_commit) as s:
        assert run(s) == ("", "ERROR")


def test_a_language_the_deployment_does_not_serve_is_treated_as_noise():
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "pa-IN")

    with make_server(rec, on_commit) as s:
        assert run(s) == ("", "")


def test_latest_partial_is_filled_in():
    rec = Recorder()
    holder = {}

    async def on_commit(ws):
        await reply(ws, "chai patti", "hi-IN")

    with make_server(rec, on_commit) as s:
        import os
        os.environ["GNANI_STT_URL"] = s.url
        session = stt_gnani.start_streaming_session("hi-IN")
        session.feed(speech())
        session.finish()
        holder["p"] = session.latest_partial
    assert holder["p"] == "chai patti"


def test_a_refused_connection_gives_the_error_marker(monkeypatch):
    monkeypatch.setenv("GNANI_STT_URL", "ws://127.0.0.1:9")    # nothing listens on the discard port
    session = stt_gnani.start_streaming_session("hi-IN")
    session.feed(speech())
    assert session.finish() == ("", "ERROR")


# ---- concurrency and staleness ----------------------------------------------

def test_a_session_whose_call_ended_abandons_the_wait_for_a_slot(monkeypatch):
    full = threading.Semaphore(0)                              # no free slots
    monkeypatch.setattr(stt_gnani, "_concurrency", full)
    monkeypatch.setenv("GNANI_STT_URL", "ws://127.0.0.1:9")
    session = stt_gnani.start_streaming_session("hi-IN", is_stale=lambda: True)
    session.feed(speech())
    t0 = time.monotonic()
    assert session.finish() == ("", "")
    assert time.monotonic() - t0 < 3


def test_the_slot_is_given_back_after_a_session():
    rec = Recorder()
    before = stt_gnani._concurrency._value
    with make_server(rec) as s:
        run(s)
        deadline = time.monotonic() + 3                 # finish() returns on the answer; the socket closes just after
        while stt_gnani._concurrency._value != before and time.monotonic() < deadline:
            time.sleep(0.02)
    assert stt_gnani._concurrency._value == before


# ---- wiring -----------------------------------------------------------------

def test_missing_key_is_reported_at_warmup(monkeypatch):
    monkeypatch.delenv("GNANI_API_KEY")
    with pytest.raises(RuntimeError, match="GNANI_API_KEY"):
        stt_gnani.warmup()


def test_the_provider_switch_selects_gnani(monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "gnani")
    from dukaan_dost import stt_provider
    try:
        importlib.reload(stt_provider)
        assert stt_provider.start_streaming_session is stt_gnani.start_streaming_session
        assert stt_provider.set_keyterms is stt_gnani.set_keyterms
    finally:
        monkeypatch.delenv("STT_PROVIDER")
        importlib.reload(stt_provider)


def test_an_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("STT_PROVIDER", "nonsense")
    from dukaan_dost import stt_provider
    try:
        with pytest.raises(ValueError, match="gnani"):
            importlib.reload(stt_provider)
    finally:
        monkeypatch.delenv("STT_PROVIDER")
        importlib.reload(stt_provider)


def test_a_server_that_never_sends_processing_finishes_quickly():
    """The real service sends speech_start and then the transcript, with no 'processing' in between
    (observed 2026-11-02). Waiting for one made every utterance take the full timeout."""
    rec = Recorder()

    async def on_commit(ws):
        await reply(ws, "do kilo atta", "hi-IN", with_processing=False)

    with make_server(rec, on_commit) as s:
        t0 = time.monotonic()
        assert run(s) == ("do kilo atta", "hi-IN")
        assert time.monotonic() - t0 < 1.5            # not the 3 s test timeout
