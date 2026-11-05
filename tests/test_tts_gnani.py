"""
Tests for the Gnani text-to-speech backend and the provider switch, run against a stand-in
server that follows the protocol at docs.gnani.ai/api/TTS/tts-websocket.md. They show the
client does what the docs say; they cannot show the real service agrees.

    python -m pytest tests/test_tts_gnani.py
"""

import base64
import importlib
import io
import json
import struct
import sys
import time
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_ws import FakeServer  # noqa: E402

from dukaan_dost import tts_gnani  # noqa: E402


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-key")
    monkeypatch.delenv("GNANI_TTS_LANGUAGE", raising=False)
    monkeypatch.setattr("dukaan_dost.tts_gnani.SPARE", False)          # the spare-connection tests switch it on
    monkeypatch.setattr("dukaan_dost.tts_gnani.with_retry",
                        lambda fn, attempts=2, delay=0.0: _retry(fn, attempts))


def _retry(fn, attempts):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
    raise last


def pcm(n_samples, value=1000):
    return struct.pack("<" + "h" * n_samples, *([value] * n_samples))


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class Seen:
    def __init__(self):
        self.headers = None
        self.requests = []


def make_server(seen, chunks, finish="complete"):
    """A stand-in Timbre: start, the given audio chunks, then complete (or an error / early close)."""
    async def handler(ws):
        seen.headers = ws.request.headers
        async for raw in ws:
            seen.requests.append(json.loads(raw))
            await ws.send(json.dumps({"type": "start", "message": "Streaming started", "request_id": "r1"}))
            for i, c in enumerate(chunks, 1):
                await ws.send(json.dumps({"type": "audio", "data": {"chunk_index": i, "audio": b64(c),
                                                                    "is_final": False}}))
            if finish == "complete":
                await ws.send(json.dumps({"type": "complete",
                                          "data": {"chunk_index": len(chunks) + 1, "audio": "", "is_final": True}}))
            elif finish == "error":
                await ws.send(json.dumps({"type": "error", "message": "Invalid text or audio configuration."}))
            elif finish == "close":
                await ws.close()
    return FakeServer(handler)


def point_at(server, monkeypatch):
    monkeypatch.setenv("GNANI_TTS_URL", server.url)


# ---- the request ------------------------------------------------------------

def test_the_request_follows_the_documented_shape(monkeypatch):
    seen = Seen()
    with make_server(seen, [pcm(100)]) as s:
        point_at(s, monkeypatch)
        list(tts_gnani.start_streaming_synthesis("Namaste", "hi-IN").chunks())
    req = seen.requests[0]
    assert seen.headers["X-API-Key-ID"] == "test-key"
    assert req["voice"] == "Shivani" and req["model"] == "timbre-v3.0" and req["language"] == "hi-IN"
    assert req["speed"] == 1.0
    assert req["audio_config"] == {"sample_rate": 16000, "num_channels": 1, "sample_width": 2,
                                   "encoding": "linear_pcm", "container": "raw"}


def test_one_request_per_synthesis_not_one_per_connection_reuse(monkeypatch):
    seen = Seen()
    with make_server(seen, [pcm(10)]) as s:
        point_at(s, monkeypatch)
        list(tts_gnani.start_streaming_synthesis("a", "en-IN").chunks())
        list(tts_gnani.start_streaming_synthesis("b", "te-IN").chunks())
    assert [r["text"] for r in seen.requests] == ["a", "b"]
    assert [r["language"] for r in seen.requests] == ["en-IN", "te-IN"]


@pytest.mark.parametrize("given, expected", [
    ("hi-in", "hi-IN"), ("te_IN", "te-IN"), ("en", "en-IN"), ("xx-YY", "en-IN"), (None, "en-IN"), ("", "en-IN"),
])
def test_language_codes_are_normalised_and_unknown_ones_fall_back(given, expected):
    assert tts_gnani._normalize_language(given) == expected


def test_a_language_override_forces_hinglish(monkeypatch):
    monkeypatch.setenv("GNANI_TTS_LANGUAGE", "hi-en")
    assert tts_gnani._normalize_language("te-IN") == "hi-en"


# ---- audio coming back --------------------------------------------------------

def test_chunks_arrive_as_raw_pcm_in_order(monkeypatch):
    seen = Seen()
    parts = [pcm(50, 1), pcm(60, 2), pcm(70, 3)]
    with make_server(seen, parts) as s:
        point_at(s, monkeypatch)
        stream = tts_gnani.start_streaming_synthesis("x", "hi-IN")
        got = list(stream.chunks())
    assert b"".join(got) == b"".join(parts) and not stream.failed
    assert stream.first_chunk_ms is not None and stream.n_chunks == 3


def test_a_chunk_that_ends_mid_sample_is_carried_to_the_next(monkeypatch):
    whole = pcm(100)
    seen = Seen()
    with make_server(seen, [whole[:51], whole[51:]]) as s:           # split inside a 16-bit sample
        point_at(s, monkeypatch)
        got = list(tts_gnani.start_streaming_synthesis("x", "hi-IN").chunks())
    assert all(len(c) % 2 == 0 for c in got) and b"".join(got) == whole


def test_synthesize_returns_a_16khz_mono_wav(monkeypatch):
    seen = Seen()
    with make_server(seen, [pcm(800), pcm(800)]) as s:
        point_at(s, monkeypatch)
        wav = tts_gnani.synthesize("namaste", "hi-IN")
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()) == (16000, 1, 2, 1600)


# ---- failures -----------------------------------------------------------------

def test_a_server_error_marks_the_stream_failed_and_synthesize_returns_none(monkeypatch):
    seen = Seen()
    with make_server(seen, [], finish="error") as s:
        point_at(s, monkeypatch)
        stream = tts_gnani.start_streaming_synthesis("x", "hi-IN")
        assert list(stream.chunks()) == [] and stream.failed
        assert tts_gnani.synthesize("x", "hi-IN") is None


def test_a_connection_that_closes_early_is_a_failure_not_a_short_clip(monkeypatch):
    seen = Seen()
    with make_server(seen, [pcm(20)], finish="close") as s:
        point_at(s, monkeypatch)
        stream = tts_gnani.start_streaming_synthesis("x", "hi-IN")
        list(stream.chunks())
        assert stream.failed


def test_an_unreachable_server_fails_without_hanging(monkeypatch):
    monkeypatch.setenv("GNANI_TTS_URL", "ws://127.0.0.1:9")
    stream = tts_gnani.start_streaming_synthesis("x", "hi-IN")
    t0 = time.monotonic()
    assert list(stream.chunks()) == [] and stream.failed
    assert time.monotonic() - t0 < 12


def test_empty_text_gives_no_audio_and_no_connection(monkeypatch):
    monkeypatch.setenv("GNANI_TTS_URL", "ws://127.0.0.1:9")
    stream = tts_gnani.start_streaming_synthesis("   ", "hi-IN")
    assert list(stream.chunks()) == [] and not stream.failed


def test_a_missing_key_fails_the_stream_and_warmup_raises(monkeypatch):
    monkeypatch.delenv("GNANI_API_KEY")
    stream = tts_gnani.start_streaming_synthesis("x", "hi-IN")
    assert list(stream.chunks()) == [] and stream.failed
    with pytest.raises(RuntimeError, match="GNANI_API_KEY"):
        tts_gnani.warmup()


def test_warmup_does_not_raise_when_the_service_is_down(monkeypatch):
    monkeypatch.setenv("GNANI_TTS_URL", "ws://127.0.0.1:9")
    tts_gnani.warmup()


# ---- text ---------------------------------------------------------------------

@pytest.mark.parametrize("raw, spoken", [
    ("Total ₹45 hua", "Total 45 rupees hua"),
    ("Rs. 260 hai", "260 rupees hai"),
    ("Rs 45.50", "45.50 rupees"),
    ("Loan 1,25,000 ka hai", "Loan 125000 ka hai"),
    ("₹1,25,000", "125000 rupees"),
    ("2 kg atta,  1.5 kg chini", "2 kg atta, 1.5 kg chini"),
    ("Hello there", "Hello there"),
])
def test_text_is_prepared_for_speech(raw, spoken):
    assert tts_gnani.normalize_text(raw) == spoken


def test_a_decimal_is_not_mangled_into_a_thousands_number():
    assert tts_gnani.normalize_text("1.5 kg") == "1.5 kg"


def test_digit_spelling_is_never_needed():
    assert tts_gnani.needs_digit_spelling("9876543210") is False


# ---- the provider switch ---------------------------------------------------------

def test_the_default_provider_is_google(monkeypatch):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    from dukaan_dost import tts_provider
    importlib.reload(tts_provider)
    assert tts_provider.TTS_PROVIDER == "google"


def test_the_gnani_provider_exposes_the_same_four_names(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "gnani")
    from dukaan_dost import tts_provider
    try:
        importlib.reload(tts_provider)
        assert tts_provider.synthesize is tts_gnani.synthesize
        assert tts_provider.start_streaming_synthesis is tts_gnani.start_streaming_synthesis
        assert tts_provider.needs_digit_spelling is tts_gnani.needs_digit_spelling
        assert tts_provider.warmup is tts_gnani.warmup
    finally:
        monkeypatch.delenv("TTS_PROVIDER")
        importlib.reload(tts_provider)


def test_an_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "nonsense")
    from dukaan_dost import tts_provider
    try:
        with pytest.raises(ValueError, match="gnani"):
            importlib.reload(tts_provider)
    finally:
        monkeypatch.delenv("TTS_PROVIDER")
        importlib.reload(tts_provider)


def test_both_backends_offer_the_names_the_app_imports():
    from dukaan_dost import tts_google
    for name in ("synthesize", "warmup", "start_streaming_synthesis", "needs_digit_spelling"):
        assert callable(getattr(tts_gnani, name)) and callable(getattr(tts_google, name))


# ---- the spare connection -------------------------------------------------------------------

def counting_server(opened):
    async def handler(ws):
        opened.append(time.monotonic())
        async for raw in ws:
            await ws.send(json.dumps({"type": "audio", "data": {"chunk_index": 1, "audio": b64(pcm(10)), "is_final": False}}))
            await ws.send(json.dumps({"type": "complete", "data": {"chunk_index": 2, "audio": "", "is_final": True}}))
    return FakeServer(handler)


def wait_until(predicate, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_the_next_sentence_uses_a_connection_opened_ahead_of_time(monkeypatch):
    monkeypatch.setattr("dukaan_dost.tts_gnani.SPARE", True)
    opened = []
    with counting_server(opened) as s:
        point_at(s, monkeypatch)
        try:
            assert list(tts_gnani.start_streaming_synthesis("a", "en-IN").chunks())      # opens one, then a spare behind it
            assert wait_until(lambda: len(opened) == 2)
            before = len(opened)
            assert list(tts_gnani.start_streaming_synthesis("b", "en-IN").chunks())      # takes the spare: no new wait
            assert wait_until(lambda: len(opened) == before + 1)                          # and a fresh spare is opened
        finally:
            tts_gnani.close_spare()


def test_a_stale_spare_is_not_used(monkeypatch):
    monkeypatch.setattr("dukaan_dost.tts_gnani.SPARE", True)
    monkeypatch.setattr("dukaan_dost.tts_gnani.SPARE_MAX_AGE_SEC", 0.0)
    opened = []
    with counting_server(opened) as s:
        point_at(s, monkeypatch)
        try:
            list(tts_gnani.start_streaming_synthesis("a", "en-IN").chunks())
            assert wait_until(lambda: len(opened) == 2)
            stream = tts_gnani.start_streaming_synthesis("b", "en-IN")
            assert list(stream.chunks()) and not stream.failed                       # works, by a new connection
        finally:
            tts_gnani.close_spare()


def test_a_spare_for_another_address_is_not_used(monkeypatch):
    monkeypatch.setattr("dukaan_dost.tts_gnani.SPARE", True)
    first, second = [], []
    with counting_server(first) as a, counting_server(second) as b:
        try:
            point_at(a, monkeypatch)
            list(tts_gnani.start_streaming_synthesis("a", "en-IN").chunks())
            assert wait_until(lambda: len(first) == 2)
            point_at(b, monkeypatch)
            assert list(tts_gnani.start_streaming_synthesis("b", "en-IN").chunks())
            assert len(second) >= 1
        finally:
            tts_gnani.close_spare()


def test_with_the_spare_switched_off_every_sentence_opens_its_own_connection(monkeypatch):
    opened = []
    with counting_server(opened) as s:
        point_at(s, monkeypatch)
        list(tts_gnani.start_streaming_synthesis("a", "en-IN").chunks())
        list(tts_gnani.start_streaming_synthesis("b", "en-IN").chunks())
        time.sleep(0.2)
        assert len(opened) == 2
