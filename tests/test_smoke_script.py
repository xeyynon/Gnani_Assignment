"""
Tests for scripts/gnani_smoke_test.py, run against stand-in servers, so the script is known to
work before it is first used with a real key.

    python -m pytest tests/test_smoke_script.py
"""

import argparse
import base64
import importlib.util
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_ws import FakeServer  # noqa: E402

from dukaan_dost import stt_gnani, tts_gnani  # noqa: E402


def load_script():
    spec = importlib.util.spec_from_file_location("gnani_smoke_test", ROOT / "scripts" / "gnani_smoke_test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_script()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-key")
    monkeypatch.setattr(stt_gnani, "COMMIT_GRACE_SEC", 0.05)
    monkeypatch.setattr(stt_gnani, "TRAILING_SILENCE_SEC", 0.1)
    monkeypatch.setattr(smoke, "SENTENCES", [("hindi", "hi-IN", "दो किलो आटा"), ("english", "en-IN", "two kilo atta")])


def tts_server():
    audio = struct.pack("<" + "h" * 1600, *([500] * 1600))

    async def handler(ws):
        async for _ in ws:
            await ws.send(json.dumps({"type": "start"}))
            await ws.send(json.dumps({"type": "audio", "data": {"chunk_index": 1, "is_final": False,
                                                                "audio": base64.b64encode(audio).decode()}}))
            await ws.send(json.dumps({"type": "complete", "data": {"chunk_index": 2, "audio": "", "is_final": True}}))
    return FakeServer(handler)


def stt_server(text):
    async def handler(ws):
        await ws.send(json.dumps({"type": "connected"}))
        async for msg in ws:
            if isinstance(msg, str) and json.loads(msg).get("type") == "commit":
                await ws.send(json.dumps({"type": "processing"}))
                await ws.send(json.dumps({"type": "transcript", "text": text, "is_final": True,
                                          "detected_language_code": "hi-IN"}))
    return FakeServer(handler)


def test_word_error_rate():
    assert smoke.word_error_rate("two kilo atta", "two kilo atta") == 0
    assert smoke.word_error_rate("two kilo atta", "two kilo") == pytest.approx(1 / 3)
    assert smoke.word_error_rate("two kilo atta", "one kilo atta please") == pytest.approx(2 / 3)
    assert smoke.word_error_rate("Do kilo, atta!", "do kilo atta") == 0           # case and punctuation ignored
    assert smoke.word_error_rate("", "") == 0 and smoke.word_error_rate("", "x") == 1


def test_the_tts_experiment_writes_wavs_and_reports_first_chunk_time(tmp_path, monkeypatch):
    with tts_server() as s:
        monkeypatch.setenv("GNANI_TTS_URL", s.url)
        result = smoke.cmd_tts(argparse.Namespace(out=str(tmp_path)))
    assert [r["ok"] for r in result["rows"]] == [True, True]
    assert all(r["first_chunk_ms"] is not None for r in result["rows"])
    assert (tmp_path / "hindi.wav").stat().st_size > 44


def test_the_round_trip_scores_what_prisma_heard(monkeypatch):
    with tts_server() as t, stt_server("two kilo atta") as s:
        monkeypatch.setenv("GNANI_TTS_URL", t.url)
        monkeypatch.setenv("GNANI_STT_URL", s.url)
        result = smoke.cmd_roundtrip(argparse.Namespace(keyterms="Maggi,Amul butter", hints=False))
    english = [r for r in result["rows"] if r["label"] == "english"][0]
    assert english["wer"] == 0 and english["heard"] == "two kilo atta"
    hindi = [r for r in result["rows"] if r["label"] == "hindi"][0]
    assert hindi["wer"] == 1.0                                   # the stand-in answered with the English text
    assert result["keyterms"] == "Maggi,Amul butter"


def test_the_concurrency_probe_reports_the_first_refusal(monkeypatch):
    opened = {"n": 0}

    async def handler(ws):
        opened["n"] += 1
        if opened["n"] > 3:
            await ws.send(json.dumps({"type": "error", "message": "concurrent session limit reached"}))
            return
        await ws.send(json.dumps({"type": "connected"}))
        await ws.wait_closed()

    with FakeServer(handler) as s:
        monkeypatch.setenv("GNANI_STT_URL", s.url)
        result = smoke.cmd_concurrency(argparse.Namespace(max=6))
    assert result["held"] == 3 and result["refused"][0] == 4 and "limit" in result["refused"][1]


def test_a_missing_key_stops_the_script_with_instructions(monkeypatch):
    monkeypatch.delenv("GNANI_API_KEY")
    monkeypatch.setitem(sys.modules, "local_config", None)       # as if there is no local_config.py
    with pytest.raises(SystemExit) as e:
        smoke.load_key()
    assert "app.gnani.ai" in str(e.value)
