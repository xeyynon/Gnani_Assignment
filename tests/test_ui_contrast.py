"""
Tests for scripts/ui_check/contrast.py and for the colours the pages actually use.

The first version of that tool read the dark colours twice and never measured the light theme, so "all pass"
meant nothing for light. These tests therefore check the tool itself (known answers, each theme reads its own
values, a bad colour fails) before they check the pages.

    python -m pytest tests/test_ui_contrast.py
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ui_check"))

import contrast  # noqa: E402


def test_the_arithmetic_matches_known_answers():
    assert contrast.ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)
    assert contrast.ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
    assert contrast.ratio("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)         # the classic just-failing grey
    assert contrast.ratio("#767676", "#FFFFFF") >= 4.5                                    # and the one that just passes
    assert contrast.ratio("#123456", "#ABCDEF") == contrast.ratio("#ABCDEF", "#123456")   # order does not matter


def test_each_theme_reads_its_own_values_not_another_themes():
    t = contrast.themes()
    assert set(t) == {"light", "dark"}
    assert t["light"]["bg"] == "#F3F3F1" and t["light"]["ink"] == "#1C1C1E"
    assert t["dark"]["bg"] == "#141415" and t["dark"]["ink"] == "#ECECEE"
    for name in t:
        assert len(t[name]) >= 20, f"{name} read only {len(t[name])} tokens"
    assert len({tuple(sorted(v.items())) for v in t.values()}) == 2                       # two genuinely different themes


def test_light_text_is_dark_and_dark_text_is_light():
    t = contrast.themes()
    assert contrast.luminance(t["light"]["ink"]) < 0.1 < 0.5 < contrast.luminance(t["light"]["bg"])
    assert contrast.luminance(t["dark"]["ink"]) > 0.5 > 0.1 > contrast.luminance(t["dark"]["bg"])


def test_a_pair_that_is_too_pale_is_reported_as_failing(monkeypatch):
    real = contrast.themes
    def pale():
        t = real()
        t["light"]["muted"] = "#9AA39D"                                                   # a pale caption colour
        return t
    monkeypatch.setattr(contrast, "themes", pale)
    failing = [r for r in contrast.measure() if r[3] is None or r[3] < r[4]]
    assert any(r[0] == "light" and r[1] == "muted" for r in failing)
    assert contrast.main([]) == 1                                                         # and the command says so with its exit code


def test_a_missing_token_is_reported_not_skipped(monkeypatch):
    real = contrast.themes
    def without():
        t = real()
        del t["dark"]["amber-soft"]
        return t
    monkeypatch.setattr(contrast, "themes", without)
    assert any(r[0] == "dark" and r[3] is None for r in contrast.measure())


def test_every_text_pair_the_pages_use_passes_in_every_theme():
    rows = contrast.measure()
    assert len(rows) == 2 * len(contrast.PAIRS)
    failing = [f"{t}: {fg} on {bg} is {got:.2f}, needs {need}" for t, fg, bg, got, need, _ in rows if got is None or got < need]
    assert failing == []


def test_the_command_succeeds_on_the_real_tokens():
    assert contrast.main([]) == 0
