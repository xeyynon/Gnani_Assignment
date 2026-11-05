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


def test_speech_loudness_is_the_whole_clip_rms_with_the_silence_in_it(tmp_path):
    """Regression (B-58): the level was taken over samples above 300 only, so a requested 10 dB gave about 7 dB."""
    import numpy as np
    p = tmp_path / "s.wav"
    pcm = np.concatenate([np.zeros(16000), (6000 * np.sin(np.arange(16000) / 5)).astype(np.int16)]).astype(np.int16)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm.tobytes())
    plain = float(np.sqrt(np.mean(pcm.astype(float) ** 2)))
    assert abs(run_calls.speech_rms([p]) - plain) < 1e-6 and 2900 < plain < 3100          # 6000 / sqrt(2) over half the clip


def test_speech_loudness_pools_the_samples_of_all_clips(tmp_path):
    import numpy as np
    paths, allsamples = [], []
    for k, (amp, n) in enumerate([(4000, 8000), (1000, 24000)]):
        a = (amp * np.sin(np.arange(n) / 3)).astype(np.int16)
        p = tmp_path / f"c{k}.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(a.tobytes())
        paths.append(p); allsamples.append(a)
    pooled = float(np.sqrt(np.mean(np.concatenate(allsamples).astype(float) ** 2)))
    assert abs(run_calls.speech_rms(paths) - pooled) < 1e-6


def fake_synth(monkeypatch, amps=None):
    """Stands in for Timbre: a short tone per text (amplitude from `amps` by text). Returns the list of syntheses made."""
    import numpy as np
    made = []

    def synth(text, lang):
        made.append((text, lang))
        return ((amps or {}).get(text, 3000) * np.sin(np.arange(1600) / 4)).astype(np.int16).tobytes()

    monkeypatch.setattr(run_calls, "_synthesize", synth)
    monkeypatch.setattr(run_calls, "_voice", lambda: "V1")
    return made


def test_a_cached_clip_is_reused_only_for_the_same_text_language_and_voice(tmp_path, monkeypatch):
    """Regression (B-59): the cache was keyed by call id and index, so edited script text played stale audio."""
    made = fake_synth(monkeypatch)
    p = tmp_path / "c1_0.wav"
    run_calls.synth_wav("do kilo cheeni", "hi-IN", p)
    assert len(made) == 1 and p.exists() and p.with_name("c1_0.wav.json").exists() and not list(tmp_path.glob("*.tmp"))
    run_calls.synth_wav("do kilo cheeni", "hi-IN", p)
    assert len(made) == 1                                                       # same text: reused
    run_calls.synth_wav("teen kilo cheeni", "hi-IN", p)
    assert len(made) == 2                                                       # edited text: made again
    run_calls.synth_wav("teen kilo cheeni", "te-IN", p)
    assert len(made) == 3                                                       # another language
    monkeypatch.setattr(run_calls, "_voice", lambda: "V2")
    run_calls.synth_wav("teen kilo cheeni", "te-IN", p)
    assert len(made) == 4                                                       # another voice


def test_a_cached_clip_with_no_sidecar_is_kept_and_given_one(tmp_path, monkeypatch):
    made = fake_synth(monkeypatch)
    p = tmp_path / "old_0.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\x01\x00" * 100)
    before = p.read_bytes()
    run_calls.synth_wav("anything", "hi-IN", p)
    assert made == [] and p.read_bytes() == before
    side = json.loads(p.with_name("old_0.wav.json").read_text(encoding="utf-8"))
    assert side["hash"] == run_calls.clip_hash("anything", "hi-IN", "V1")
    run_calls.synth_wav("anything else", "hi-IN", p)                          # now it has a sidecar, so a change is noticed
    assert len(made) == 1


def test_the_model_and_provider_come_from_the_agent_log(tmp_path):
    """Regression (B-61): the model was recorded as the word 'default' when LLM_MODEL was unset."""
    log = tmp_path / "a.log"
    log.write_text("01:03:52 [INFO] LLM=openai/gpt-oss-120b (Groq) | User location=India\n", encoding="utf-8")
    assert run_calls.llm_from_log(log, None) == {"model": "openai/gpt-oss-120b", "llm_provider": "Groq", "model_source": "agent log"}
    log.write_text("nothing here\n", encoding="utf-8")
    assert run_calls.llm_from_log(log, "m-env")["model"] == "m-env"
    assert run_calls.llm_from_log(tmp_path / "missing.log", None)["model"] == "unknown"


def run_main_with_fake_agent(tmp_path, monkeypatch, *, poll, raw, argv_extra=(),
                             log_text="01:00:00 [INFO] LLM=gem-x (Gemini API key) | User\n"):
    """Runs run_calls.main() with a stand-in for the agent process (call fake_synth first): nothing is started, no network."""
    monkeypatch.setattr(run_calls, "ROOT", tmp_path)
    monkeypatch.setattr(run_calls.time, "sleep", lambda s: None)
    sp = tmp_path / "scr.json"
    sp.write_text(json.dumps({"calls": [{"id": "a", "turns": [{"text": "x"}]}, {"id": "b", "turns": [{"text": "y"}]}]}), encoding="utf-8")
    out = tmp_path / "res" / "run.json"
    out.parent.mkdir()

    class FakeProc:
        def __init__(self, cmd, cwd=None, env=None, stdout=None, stderr=None):
            stdout.write(log_text); stdout.flush()
            if raw is not None:
                Path(json.loads(Path(env["REPLAY_PLAN"]).read_text(encoding="utf-8"))["results"]).write_text(json.dumps(raw), encoding="utf-8")

        def poll(self):
            return poll

        def terminate(self): pass
        def wait(self, t=None): return 0
        def kill(self): pass

    monkeypatch.setattr(run_calls.subprocess, "Popen", FakeProc)
    monkeypatch.setattr(sys, "argv", ["run_calls.py", str(sp), "--out", str(out), *argv_extra])
    run_calls.main()
    return json.loads(out.read_text(encoding="utf-8"))


def test_a_run_that_finished_every_call_is_recorded_complete_with_the_real_model(tmp_path, monkeypatch):
    fake_synth(monkeypatch)
    res = run_main_with_fake_agent(tmp_path, monkeypatch, poll=None, raw={"done": True, "calls": [{"id": "a"}, {"id": "b"}]})
    assert res["complete"] is True and res["timed_out"] is False and res["agent_exited_early"] is False
    assert res["model"] == "gem-x" and res["llm_provider"] == "Gemini API key"


def test_an_agent_that_dies_early_is_flagged_and_the_run_is_not_complete(tmp_path, monkeypatch, capsys):
    fake_synth(monkeypatch)
    res = run_main_with_fake_agent(tmp_path, monkeypatch, poll=1, raw={"done": False, "calls": [{"id": "a"}]})
    assert res["agent_exited_early"] is True and res["complete"] is False and res["calls_finished"] == 1 and res["calls_expected"] == 2
    assert "EXITED EARLY" in capsys.readouterr().out


def test_a_run_that_times_out_is_flagged(tmp_path, monkeypatch, capsys):
    fake_synth(monkeypatch)
    res = run_main_with_fake_agent(tmp_path, monkeypatch, poll=None, raw={"done": False, "calls": []}, argv_extra=["--timeout", "0"])
    assert res["timed_out"] is True and res["complete"] is False
    assert "TIMED OUT" in capsys.readouterr().out


def test_a_done_flag_without_every_call_is_not_complete(tmp_path, monkeypatch):
    fake_synth(monkeypatch)
    res = run_main_with_fake_agent(tmp_path, monkeypatch, poll=None, raw={"done": True, "calls": [{"id": "a"}]})
    assert res["complete"] is False


def test_the_noise_level_is_the_same_whatever_the_only_subset(tmp_path, monkeypatch):
    """Regression (B-58): the speech level was measured on the calls kept by --only, so the noise changed with the subset."""
    levels = {}
    for only in ("a", "a,b"):
        sub = tmp_path / only.replace(",", "_")
        sub.mkdir()
        fake_synth(monkeypatch, amps={"x": 2000, "y": 9000})
        res = run_main_with_fake_agent(sub, monkeypatch, poll=1, raw=None, argv_extra=["--noise", "10", "--only", only])
        levels[only] = (res["speech_rms"], res["noise_gain"])
        assert "whole-clip RMS" in res["snr_definition"]
    assert levels["a"] == levels["a,b"]


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


# ---- scorer fixes: B-57, B-60, B-72, B-73, B-74, B-75 ----------------------------------------------

STOCK_SKUS = {"sugar": "SUGAR-1KG", "rice": "RICE-1KG"}


def score_run(tmp_path, monkeypatch, script_calls, run_calls_list, *, log="ok", done=True, extra_args=(), orders=(), loans=(), expected=None):
    """Writes a script, a run result, orders and an agent log, runs the scorer, and returns (summary dict, markdown)."""
    shop = tmp_path / "orders" / "dukaan_dost"
    shop.mkdir(parents=True, exist_ok=True)
    for i, o in enumerate(orders):
        (shop / f"order_{i}.json").write_text(json.dumps(o), encoding="utf-8")
    for i, o in enumerate(loans):
        (shop / f"loan_{i}.json").write_text(json.dumps(o), encoding="utf-8")
    sname = "_test_score_fix.json"
    (ROOT / "evaluation" / "scripts" / sname).write_text(json.dumps({"calls": script_calls}), encoding="utf-8")
    try:
        run = {"script": sname, "noise_snr_db": None, "elapsed_sec": 1, "model": "m", "orders_dir": str(tmp_path / "orders"),
               "run": {"done": done, "calls": run_calls_list}}
        if expected is not None:
            run["expected"] = expected
        runp = tmp_path / "run.json"
        runp.write_text(json.dumps(run), encoding="utf-8")
        if log is not None:
            (tmp_path / "run.agent.log").write_text("" if log == "ok" else log, encoding="utf-8")
        out = tmp_path / "s.json"
        monkeypatch.setattr(sys, "argv", ["score_calls.py", str(runp), "--out", str(out), *extra_args])
        score.main()
    finally:
        (ROOT / "evaluation" / "scripts" / sname).unlink()
    return json.loads(out.read_text(encoding="utf-8")), out.with_suffix(".md").read_text(encoding="utf-8")


def sugar_call(cid="x1", begin="2026-11-03T10:00:00+05:30", end="2026-11-03T10:01:00+05:30", turns=None):
    return {"id": cid, "begin_iso": begin, "end_iso": end,
            "turns": turns if turns is not None else [{"i": 0, "text": "x", "heard": ["x"], "first_audio_after_ms": 1000}]}


SUGAR_SCRIPT = {"id": "x1", "lang": "en-IN", "tags": [], "turns": [], "expected": {"items": {"SUGAR-1KG": 1}, "payment": "cash"}}
SUGAR_ORDER = {"time": "2026-11-03T10:00:30+05:30", "payment": "cash", "total": 44, "items": [{"sku": "SUGAR-1KG", "qty": 1, "line_total": 44}]}


def test_time_to_first_audio_counts_from_the_callers_last_word_not_the_end_of_the_file(tmp_path, monkeypatch):
    """Regression (B-57): the Timbre clips end with a pause, so the time from the end of the file was too small."""
    import numpy as np
    pcm = np.concatenate([(8000 * np.sin(np.arange(8000) / 7)).astype(np.int16), np.zeros(4800, dtype=np.int16)])      # 0.3 s of quiet
    wav = tmp_path / "t.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm.tobytes())
    turns = [{"i": 0, "text": "x", "heard": ["x"], "first_audio_after_ms": 1000, "audio": str(wav)},                      # old result: measured from the wav
             {"i": 1, "text": "x", "heard": ["x"], "first_audio_after_ms": 2000, "trailing_silence_ms": 400}]             # new result: recorded
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT], [sugar_call(turns=turns)], orders=[SUGAR_ORDER])
    assert s["time_to_first_audio_from_clip_end_ms"]["median"] == 1500 and s["time_to_first_audio_ms"]["median"] == 1850      # (1300, 2400)
    assert s["time_to_first_audio_ms"]["turns_without_silence_correction"] == 0
    assert "from the caller's last word" in md and "from the end of the audio file" in md and "uncorrected" in md


def test_a_turn_whose_clip_is_missing_is_left_uncorrected_and_the_output_says_so(tmp_path, monkeypatch):
    turns = [{"i": 0, "text": "x", "heard": ["x"], "first_audio_after_ms": 1000, "audio": str(tmp_path / "gone.wav")},
             {"i": 1, "text": "x", "heard": ["x"], "first_audio_after_ms": 1200}]
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT], [sugar_call(turns=turns)], orders=[SUGAR_ORDER])
    assert s["time_to_first_audio_ms"]["median"] == 1100 and s["time_to_first_audio_ms"]["turns_without_silence_correction"] == 2
    assert "2 of 2 turns could not be corrected" in md


def test_a_run_that_stopped_early_is_not_valid(tmp_path, monkeypatch):
    """Regression (B-60): valid_run only looked at rate limits, so a truncated run was reported valid."""
    other = {"id": "x2", "lang": "en-IN", "tags": [], "turns": [], "expected": {"items": {"RICE-1KG": 1}, "payment": "cash"}}
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT, other], [sugar_call()], orders=[SUGAR_ORDER], done=False)
    assert s["valid_run"] is False and s["complete"] is False and s["calls_finished"] == 1 and s["calls_expected"] == 2
    assert "INCOMPLETE RUN: 1 of 2 scripted calls finished" in md and "x2" in md
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT, other], [sugar_call()], orders=[SUGAR_ORDER], done=True)       # done flag but a call is missing
    assert s["valid_run"] is False and "INCOMPLETE RUN" in md
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT], [sugar_call()], orders=[SUGAR_ORDER], done=True)
    assert s["valid_run"] is True and "INCOMPLETE" not in md


def test_an_only_subset_run_is_complete_when_its_own_calls_all_finished(tmp_path, monkeypatch):
    other = {"id": "x2", "lang": "en-IN", "tags": [], "turns": [], "expected": {"items": {"RICE-1KG": 1}, "payment": "cash"}}
    s, _ = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT, other], [sugar_call()], orders=[SUGAR_ORDER], expected={"x1": {}})
    assert s["valid_run"] is True


def test_a_call_that_saved_nothing_does_not_take_the_next_calls_record():
    """Regression (B-72): call N's window ran 5 s into call N+1 and the first match won."""
    a = {"id": "a", "begin_iso": "2026-11-03T10:00:00+05:30", "end_iso": "2026-11-03T10:01:00+05:30"}
    b = {"id": "b", "begin_iso": "2026-11-03T10:01:00+05:30", "end_iso": "2026-11-03T10:02:00+05:30"}
    late = {"time": "2026-11-03T10:01:03+05:30", "who": "b"}            # b's order, 3 s into b (and inside the old [begin-5, end+5] of a)
    assert score.assign_records([a, b], [late]) == [None, late]
    assert score.order_for(a, [late]) is None
    early = {"time": "2026-11-03T10:00:59+05:30", "who": "b"}           # stamped just before b's recorded begin: nearer to b than to a
    assert score.assign_records([a, b], [early]) == [None, early]


def test_each_record_goes_to_one_call_only_and_the_nearest_record_wins():
    a = {"id": "a", "begin_iso": "2026-11-03T10:00:00+05:30", "end_iso": "2026-11-03T10:01:00+05:30"}
    b = {"id": "b", "begin_iso": "2026-11-03T10:00:10+05:30", "end_iso": "2026-11-03T10:01:00+05:30"}
    r1 = {"time": "2026-11-03T10:00:12+05:30"}
    assert score.assign_records([a, b], [r1]) == [None, r1]             # b's begin is nearer; a gets nothing, not a copy
    r0 = {"time": "2026-11-03T10:00:03+05:30"}
    assert score.assign_records([a, b], [r1, r0]) == [r0, r1]


def test_loan_calls_do_not_inflate_the_order_figures(tmp_path, monkeypatch):
    """Regression (B-73): a loan call counted as payment right, recall 1.0 and precision 1.0."""
    loan_script = {"id": "L1", "kind": "loan", "lang": "hi-IN", "tags": ["loan"], "turns": [],
                   "expected": {"project_cost": 1000000, "loan_amount": 900000, "monthly_instalment": 15438}}
    loan = {"time": "2026-11-03T10:05:30+05:30", "project_cost": 1000000, "loan_amount": 900000, "monthly_instalment": 1}
    calls = [sugar_call(), sugar_call("L1", "2026-11-03T10:05:00+05:30", "2026-11-03T10:06:00+05:30")]
    bad_order = dict(SUGAR_ORDER, payment="upi")                         # the order call: payment wrong, items right
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT, loan_script], calls, orders=[bad_order], loans=[loan])
    assert s["overall"]["calls"] == 1 and s["overall"]["payment_right"] == 0 and s["overall"]["item_recall"] == 1.0
    assert s["loans"]["calls"] == 1 and s["loans"]["exact"] == 0
    assert "| Payment chosen correctly (orders only) | 0/1 |" in md and "Loan calls: exact | 0/1" in md
    assert "L1 (loan): got" in md and "'monthly_instalment': 1" in md and "expected {'project_cost': 1000000" in md
    assert "L1: missing []" not in md
    assert "hi-IN" not in s["by_language"] and "loan" not in s["by_tag"]


def test_a_generic_hindi_word_does_not_make_an_english_word_right():
    """Regression (B-74): 'oil' got का and तेल, 'biscuits' got जी, डे, गुड."""
    items = [{"name": {"en": "Sunflower oil (1 L)", "hi": "सनफ्लावर तेल का", "te": "సన్‌ఫ్లవర్ నూనె"}, "aliases": []},
             {"name": {"en": "Mustard oil (1 L)", "hi": "सरसों तेल का", "te": "ఆవ నూనె"}, "aliases": []},
             {"name": {"en": "Good Day biscuits", "hi": "गुड डे बिस्कुट", "te": "గుడ్ డే బిస్కెట్"}, "aliases": ["biscuits"]},
             {"name": {"en": "Marie biscuits", "hi": "मैरी बिस्कुट", "te": "మేరీ బిస్కెట్"}, "aliases": ["biscuits"]},
             {"name": {"en": "Sugar", "hi": "चीनी", "te": "పంచదార"}, "aliases": ["cheeni"]}]
    v = score.english_variants(items)
    assert "oil" not in v and "biscuits" not in v
    ref = score.words("oil and biscuits")
    assert score.t_wer(ref, score.words("तेल का जी डे बिस्कुट"), v) == (3, 3)          # generic or shared words: all three still missed
    assert score.t_wer(score.words("sugar"), score.words("चीनी"), v) == (0, 1)         # a word that identifies the product counts
    assert score.t_wer(score.words("sunflower"), score.words("सनफ्लावर"), v) == (0, 1)
    assert score.t_wer(score.words("sunflower"), score.words("का तेल"), v) == (1, 1)


def test_a_missing_agent_log_means_the_run_cannot_be_verified(tmp_path, monkeypatch):
    """Regression (B-75a): no log was read as no rate limiting."""
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT], [sugar_call()], orders=[SUGAR_ORDER], log=None)
    assert s["valid_run"] is False and s["agent_log_found"] is False and "CANNOT VERIFY" in md
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT], [sugar_call()], orders=[SUGAR_ORDER], log=None, extra_args=["--no-log-ok"])
    assert s["valid_run"] is True and "CANNOT VERIFY" not in md


def test_gemini_quota_failures_make_a_run_invalid(tmp_path, monkeypatch):
    """Regression (B-75b): only Groq's '429 Too Many Requests' text was recognised."""
    log = ("00:10:01 [ERROR] [GEMINI] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota'}}\n"
           "00:10:09 [ERROR] [GEMINI-STREAM] all attempts failed: RESOURCE_EXHAUSTED\n")
    s, md = score_run(tmp_path, monkeypatch, [SUGAR_SCRIPT], [sugar_call()], orders=[SUGAR_ORDER], log=log)
    assert s["valid_run"] is False and s["rate_limited_requests"] == 2 and "INVALID RUN" in md


def test_one_refused_request_is_counted_once_not_once_per_log_line():
    """Regression (B-75c): the httpx line and the provider's 'attempt failed' line both matched, so 60 refusals showed as 120."""
    log = ("00:50:28 [INFO] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions \"HTTP/1.1 429 Too Many Requests\"\n"
           "00:50:28 [ERROR] [GROQ] attempt 1/2 failed: Client error '429 Too Many Requests' for url 'https://api.groq.com/x'\n"
           "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429 | {\"error\": \"rate_limit_exceeded\"}\n"
           "00:50:31 [INFO] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions \"HTTP/1.1 429 Too Many Requests\"\n"
           "00:50:31 [ERROR] [GROQ] attempt 2/2 failed: Client error '429 Too Many Requests' for url 'https://api.groq.com/x'\n"
           "00:50:40 [INFO] HTTP Request: POST https://api.groq.com/x \"HTTP/1.1 200 OK\"\n")
    assert score.refused_requests(log) == 2
    assert score.refused_requests("") == 0


def test_keep_awake_is_harmless_everywhere(monkeypatch):
    """Windows only; on other systems, or if the call fails, it just says False and never raises."""
    monkeypatch.setattr(run_calls.sys, "platform", "linux")
    assert run_calls.keep_awake(True) is False
    monkeypatch.setattr(run_calls.sys, "platform", "win32")
    import ctypes
    monkeypatch.setattr(ctypes, "windll", None, raising=False)
    assert run_calls.keep_awake(True) is False
