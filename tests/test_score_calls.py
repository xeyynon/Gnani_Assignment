"""
Tests for the evaluation scorer (evaluation/score_calls.py) and the run helpers. A scorer that is wrong
would make every number in the README wrong, so its arithmetic is checked here.

    python -m pytest tests/test_score_calls.py
"""

import importlib.util
import json
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "evaluation" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


score = load("score_calls")
run_calls = load("run_calls")


def test_word_error_rate_counts_substitutions_insertions_and_deletions():
    assert score.wer("a b c".split(), "a b c".split()) == (0, 3)
    assert score.wer("a b c".split(), "a x c".split()) == (1, 3)
    assert score.wer("a b c".split(), "a b".split()) == (1, 3)
    assert score.wer("a b".split(), "a b c d".split()) == (2, 2)
    assert score.wer([], "x".split()) == (1, 0)


def test_words_ignore_case_and_punctuation_but_keep_decimals_and_indian_scripts():
    assert score.words("Do kilo, atta!") == ["do", "kilo", "atta"]
    assert score.words("1.5 kg चीनी।") == ["1.5", "kg", "चीनी"]
    assert score.words("రెండు కిలోల బియ్యం.") == ["రెండు", "కిలోల", "బియ్యం"]


def test_number_normalisation_treats_spoken_numbers_and_digits_alike():
    a = score.words("two kilo sugar", True)
    b = score.words("2 kg sugar", True)
    assert a == b
    assert score.words("दो किलो", True)[0] == "2" and score.words("ek litre", True)[0] == "1"
    assert score.wer(score.words("do kilo", True), score.words("2 kilo", True))[0] == 0
    assert score.wer(score.words("do kilo"), score.words("2 kilo"))[0] == 1          # raw WER counts it as an error


def test_confidence_interval_is_sensible():
    lo, hi = score.wilson(10, 20)
    assert 0.29 < lo < 0.30 and 0.70 < hi < 0.71
    assert score.wilson(0, 0) == (0.0, 0.0)
    lo, hi = score.wilson(20, 20)
    assert hi == 1.0 and lo > 0.8


def test_percentiles():
    vals = [100, 200, 300, 400, 500]
    assert score.pct(vals, 0.5) == 300 and score.pct(vals, 0.9) == 460 and score.pct([], 0.5) is None


def test_line_totals_round_half_up_like_the_agent():
    assert score.line_total(35, 0.5) == 18 and score.line_total(60, 2) == 120 and score.line_total(30, 0.25) == 8


def test_an_order_is_matched_to_the_call_it_was_taken_in():
    rec = {"begin_iso": "2026-11-03T10:00:00+05:30", "end_iso": "2026-11-03T10:01:00+05:30"}
    inside = {"time": "2026-11-03T10:00:03+05:30", "id": 1}
    before = {"time": "2026-11-03T09:00:00+05:30", "id": 2}
    after = {"time": "2026-11-03T10:30:00+05:30", "id": 3}
    assert score.order_for(rec, [before, after, inside]) is inside
    assert score.order_for(rec, [before, after]) is None
    assert score.order_for(rec, [{"time": "garbage"}, {}]) is None


def test_a_whole_run_is_scored(tmp_path, monkeypatch):
    shop = tmp_path / "orders" / "dukaan_dost"
    shop.mkdir(parents=True)
    (shop / "order_a.json").write_text(json.dumps({
        "time": "2026-11-03T10:00:03+05:30", "payment": "cash", "total": 88, "customer": "Ramesh",
        "items": [{"sku": "SUGAR-1KG", "qty": 2, "line_total": 88}]}), encoding="utf-8")
    (shop / "order_b.json").write_text(json.dumps({
        "time": "2026-11-03T10:05:03+05:30", "payment": "upi", "total": 165 * 8, "customer": None,
        "items": [{"sku": "OIL-1L", "qty": 8, "line_total": 1320}]}), encoding="utf-8")
    script = {"calls": [
        {"id": "x1", "lang": "hi-IN", "tags": ["hindi"], "turns": [], "expected": {"items": {"SUGAR-1KG": 2}, "payment": "cash", "customer": "Ramesh"}},
        {"id": "x2", "lang": "te-IN", "tags": ["telugu", "change"], "turns": [], "expected": {"items": {"OIL-1L": 1}, "payment": "upi"}},
        {"id": "x3", "lang": "en-IN", "tags": ["english"], "turns": [], "expected": {"items": {"RICE-1KG": 1}, "payment": "cash"}}]}
    sname = "_test_score_script.json"
    (ROOT / "evaluation" / "scripts" / sname).write_text(json.dumps(script), encoding="utf-8")
    try:
        def call(cid, begin, end, heard, ms):
            return {"id": cid, "begin_iso": begin, "end_iso": end,
                    "turns": [{"i": 0, "text": "do kilo cheeni", "heard": [heard], "first_audio_after_ms": ms}]}
        run = {"script": sname, "noise_snr_db": None, "elapsed_sec": 1, "model": "m", "orders_dir": str(tmp_path / "orders"),
               "run": {"calls": [call("x1", "2026-11-03T10:00:00+05:30", "2026-11-03T10:01:00+05:30", "2 kilo cheeni", 2000),
                                 call("x2", "2026-11-03T10:05:00+05:30", "2026-11-03T10:06:00+05:30", "8 litre oil", 3000),
                                 call("x3", "2026-11-03T10:10:00+05:30", "2026-11-03T10:11:00+05:30", "", None)]}}
        runp = tmp_path / "run.json"
        runp.write_text(json.dumps(run), encoding="utf-8")
        out = tmp_path / "scored.json"
        monkeypatch.setattr(sys, "argv", ["score_calls.py", str(runp), "--out", str(out)])
        score.main()
    finally:
        (ROOT / "evaluation" / "scripts" / sname).unlink()
    s = json.loads(out.read_text(encoding="utf-8"))
    assert s["overall"]["calls"] == 3 and s["overall"]["exact_orders"] == 1
    rows = {r["id"]: r for r in s["calls_detail"]}
    assert rows["x1"]["exact"] is True and rows["x1"]["payment_right"] is True
    assert rows["x2"]["exact"] is False and rows["x2"]["wrong_quantities"] == {"OIL-1L": [1.0, 8.0]}
    assert rows["x3"]["order_saved"] is False and rows["x3"]["missing_items"] == ["RICE-1KG"]
    assert s["total_matches_stock_list"] == "2/2"
    assert s["time_to_first_audio_ms"]["n"] == 2 and s["turns_without_response"] == 1
    assert s["by_language"]["hi-IN"]["exact_orders"] == 1 and s["by_tag"]["change"]["calls"] == 1
    assert out.with_suffix(".md").read_text(encoding="utf-8").startswith("# run: clean")


def test_the_generated_noise_has_the_requested_loudness_relation(tmp_path):
    p = tmp_path / "n.wav"
    run_calls.make_noise(p, seconds=2)
    import numpy as np
    with wave.open(str(p), "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    assert len(a) == 32000 and 2500 < np.sqrt(np.mean(a ** 2)) < 3500


def test_speech_loudness_is_measured_on_the_speech_not_the_silence(tmp_path):
    import numpy as np
    p = tmp_path / "s.wav"
    pcm = np.concatenate([np.zeros(16000), (6000 * np.sin(np.arange(16000) / 5)).astype(np.int16)]).astype(np.int16)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm.tobytes())
    assert 3500 < run_calls.speech_rms([p]) < 4500            # about 6000 / sqrt(2), unaffected by the silent half


def test_a_run_whose_model_requests_were_refused_is_marked_invalid(tmp_path, monkeypatch):
    sname = "_test_score_invalid.json"
    (ROOT / "evaluation" / "scripts" / sname).write_text(json.dumps({"calls": [
        {"id": "x1", "lang": "en-IN", "tags": [], "turns": [], "expected": {"items": {"RICE-1KG": 1}, "payment": "cash"}}]}), encoding="utf-8")
    try:
        run = {"script": sname, "noise_snr_db": None, "elapsed_sec": 1, "model": "m", "orders_dir": str(tmp_path / "o"),
               "run": {"calls": [{"id": "x1", "begin_iso": "2026-11-03T10:00:00+05:30", "end_iso": "2026-11-03T10:01:00+05:30", "turns": []}]}}
        runp = tmp_path / "run.json"
        runp.write_text(json.dumps(run), encoding="utf-8")
        (tmp_path / "run.agent.log").write_text("x\n[GROQ] 429 Too Many Requests\n429 Too Many Requests\n", encoding="utf-8")
        out = tmp_path / "s.json"
        monkeypatch.setattr(sys, "argv", ["score_calls.py", str(runp), "--out", str(out)])
        score.main()
    finally:
        (ROOT / "evaluation" / "scripts" / sname).unlink()
    s = json.loads(out.read_text(encoding="utf-8"))
    assert s["valid_run"] is False and s["rate_limited_requests"] == 2
    assert "INVALID RUN" in out.with_suffix(".md").read_text(encoding="utf-8")


def test_credit_and_loan_calls_are_scored_on_their_own_expectations(tmp_path, monkeypatch):
    shop = tmp_path / "orders" / "dukaan_dost"
    shop.mkdir(parents=True)
    (shop / "order_a.json").write_text(json.dumps({
        "time": "2026-11-03T10:00:03+05:30", "payment": "udhaar", "status": "confirmed", "total": 44, "customer": "Ramesh",
        "balance_after": 444, "items": [{"sku": "SUGAR-1KG", "qty": 1, "line_total": 44}]}), encoding="utf-8")
    (shop / "loan_b.json").write_text(json.dumps({
        "time": "2026-11-03T10:05:03+05:30", "project_cost": 1000000, "loan_amount": 900000, "monthly_instalment": 15438}), encoding="utf-8")
    script = {"calls": [
        {"id": "U1", "lang": "hi-en", "tags": ["credit"], "turns": [], "expected": {"items": {"SUGAR-1KG": 1}, "payment": "udhaar", "status": "confirmed", "balance_after": 444}},
        {"id": "L1", "kind": "loan", "lang": "hi-IN", "tags": ["loan"], "turns": [], "expected": {"project_cost": 1000000, "loan_amount": 900000, "monthly_instalment": 15438}},
        {"id": "L2", "kind": "loan", "lang": "te-IN", "tags": ["loan"], "turns": [], "expected": {"project_cost": 500000, "loan_amount": 450000, "monthly_instalment": 7719}},
        {"id": "U4", "lang": "en-IN", "tags": ["credit"], "turns": [], "expected": {"items": {}, "payment": None, "no_order": True, "says": ["1900"]}},
        {"id": "U5", "lang": "en-IN", "tags": ["credit"], "turns": [], "expected": {"items": {"SUGAR-1KG": 1}, "payment": "udhaar", "status": "credit_pending", "balance_after": None}}]}
    sname = "_test_score_credit.json"
    (ROOT / "evaluation" / "scripts" / sname).write_text(json.dumps(script), encoding="utf-8")
    try:
        def call(cid, begin, end, said=()):
            return {"id": cid, "begin_iso": begin, "end_iso": end,
                    "turns": [{"i": 0, "text": "x", "heard": ["x"], "first_audio_after_ms": 1000, "agent_said": list(said)}]}
        run = {"script": sname, "noise_snr_db": None, "elapsed_sec": 1, "model": "m", "orders_dir": str(tmp_path / "orders"),
               "run": {"calls": [call("U1", "2026-11-03T10:00:00+05:30", "2026-11-03T10:01:00+05:30"),
                                 call("L1", "2026-11-03T10:05:00+05:30", "2026-11-03T10:06:00+05:30"),
                                 call("L2", "2026-11-03T10:07:00+05:30", "2026-11-03T10:08:00+05:30"),
                                 call("U4", "2026-11-03T10:09:00+05:30", "2026-11-03T10:10:00+05:30", ["Anita, you owe 1900 rupees."]),
                                 call("U5", "2026-11-03T10:11:00+05:30", "2026-11-03T10:12:00+05:30")]}}
        runp = tmp_path / "run.json"
        runp.write_text(json.dumps(run), encoding="utf-8")
        out = tmp_path / "s.json"
        monkeypatch.setattr(sys, "argv", ["score_calls.py", str(runp), "--out", str(out)])
        score.main()
    finally:
        (ROOT / "evaluation" / "scripts" / sname).unlink()
    rows = {r["id"]: r for r in json.loads(out.read_text(encoding="utf-8"))["calls_detail"]}
    assert rows["U1"]["exact"] is True and rows["U1"]["balance_right"] and rows["U1"]["status_right"]
    assert rows["L1"]["exact"] is True and rows["L1"]["loan_right"] == {"project_cost": True, "loan_amount": True, "monthly_instalment": True}
    assert rows["L2"]["exact"] is False and rows["L2"]["order_saved"] is False           # no quote was saved
    assert rows["U4"]["exact"] is True                                                    # no order, and the balance was said
    assert rows["U5"]["exact"] is False


# ---- T-WER and cut-off --------------------------------------------------------------------

ITEMS = [{"name": {"en": "Maggi Noodles (70 g)", "hi": "मैगी नूडल्स", "te": "మ్యాగీ నూడుల్స్"}, "aliases": ["maggi"]},
         {"name": {"en": "Sugar", "hi": "चीनी", "te": "పంచదార"}, "aliases": ["cheeni"]}]


def test_an_english_word_is_right_in_latin_letters_or_as_the_same_product_in_another_script():
    v = score.english_variants(ITEMS)
    ref = score.words("do packet maggi aur sugar")
    assert score.t_wer(ref, ref, v) == (0, 5)               # every Latin word counts, including Hinglish ones
    assert score.t_wer(score.words("one maggi and sugar"), score.words("one मैगी and चीनी"), v)[0] == 0
    assert score.t_wer(score.words("one maggi and sugar"), score.words("one mango and sugar"), v) == (1, 4)


def test_only_latin_words_count_in_t_wer():
    v = score.english_variants(ITEMS)
    assert score.t_wer(score.words("दो packet चीनी"), score.words("दो packet"), v) == (0, 1)
