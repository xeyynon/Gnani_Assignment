"""
Tests for the admin activity log: what gets written when the operator changes something, what never does, and how a
damaged log is read.

    python -m pytest tests/test_admin_activity.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import admin, admin_actions as act  # noqa: E402


@pytest.fixture
def log(tmp_path):
    return tmp_path / "data" / "admin_log.jsonl"


def test_an_event_is_one_line_with_a_time_a_kind_a_shop_and_a_detail(log):
    act.log_event("set_pin", "alpha", "PIN changed (chosen)", log)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert set(entry) == {"at", "kind", "shop", "detail"} and entry["shop"] == "alpha" and entry["at"].endswith("+05:30")


def test_the_log_is_listed_newest_first_and_limited(log):
    for i in range(10):
        act.log_event("save_stock", "alpha", f"change {i}", log)
    got = act.recent_activity(3, log)
    assert [e["detail"] for e in got] == ["change 9", "change 8", "change 7"]


def test_a_missing_log_reads_as_empty(tmp_path):
    assert act.recent_activity(30, tmp_path / "nothing.jsonl") == []


def test_a_damaged_line_is_skipped_not_fatal(log):
    act.log_event("create_shop", "alpha", "ok", log)
    with open(log, "a", encoding="utf-8") as f:
        f.write("{broken\n[1, 2]\n{\"no\": \"time or kind\"}\n")
    act.log_event("set_pin", "alpha", "later", log)
    assert [e["detail"] for e in act.recent_activity(30, log)] == ["later", "ok"]


def test_a_very_long_detail_and_odd_values_are_cut_down_safely(log):
    act.log_event("x" * 500, 12345, "d" * 5000, log)
    entry = act.recent_activity(1, log)[0]
    assert len(entry["kind"]) <= 40 and len(entry["detail"]) == act.MAX_DETAIL_CHARS and entry["shop"] is None


def test_only_the_tail_of_a_huge_log_is_read_and_a_cut_line_is_dropped(log, monkeypatch):
    monkeypatch.setattr(act, "LOG_TAIL_BYTES", 300)
    for i in range(40):
        act.log_event("save_stock", "alpha", f"change {i}", log)
    got = act.recent_activity(100, log)
    assert got and len(got) < 40 and got[0]["detail"] == "change 39"
    assert all(e["detail"].startswith("change ") for e in got)           # no half-read line came through as an entry


# ---- what describe() says (and never says) -------------------------------------

def test_describing_each_command():
    assert admin.describe({"cmd": "create_shop", "template": "blank"}, {"name": "new", "pin_generated": True}) == ("new", "created as a blank shop; PIN made up")
    assert admin.describe({"cmd": "create_shop", "template": "alpha"}, {"name": "new", "pin_generated": False}) == ("new", "created as a copy of alpha; PIN chosen")
    assert admin.describe({"cmd": "set_pin", "shop": "a"}, {"pin_generated": False}) == ("a", "PIN changed (chosen)")
    assert admin.describe({"cmd": "save_prompt", "shop": "a"}, {}) == ("a", "name and instructions saved")
    assert admin.describe({"cmd": "save_stock", "shop": "a", "update": [1, 2], "remove": ["X"], "add": []}, {}) == ("a", "stock saved: 2 changed, 1 removed, 0 added")
    assert admin.describe({"cmd": "dismiss", "id": "a:no-pin", "note": "later"}, {}) == ("a", "marked solved: a:no-pin (later)")
    assert admin.describe({"cmd": "restore", "id": "a:no-pin"}, {}) == ("a", "brought back: a:no-pin")


def test_reading_a_shop_is_not_an_event():
    assert admin.describe({"cmd": "get_shop", "shop": "a"}, {}) is None
    assert admin.describe({"cmd": "nonsense"}, {}) is None


def test_a_pin_or_a_prompt_never_reaches_the_log_text():
    said = admin.describe({"cmd": "set_pin", "shop": "a", "pin": "987654"}, {"pin": "987654", "pin_generated": False})[1]
    assert "987654" not in said
    said = admin.describe({"cmd": "save_prompt", "shop": "a", "system_prompt": "SECRET INSTRUCTIONS"}, {})[1]
    assert "SECRET" not in said
    said = admin.describe({"cmd": "create_shop", "template": "blank", "pin": "424242"}, {"name": "n", "pin": "424242", "pin_generated": False})[1]
    assert "424242" not in said
