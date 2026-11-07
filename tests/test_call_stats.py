"""The per-call tally (call_stats.py) and the call records on the dashboard (store.py)."""

import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import store  # noqa: E402
from dukaan_dost.call_stats import CallStats  # noqa: E402


def test_a_call_that_never_began_leaves_no_record():
    assert CallStats().finish("nothing") is None


def test_a_call_is_counted_and_the_tally_is_cleared_after_finish():
    s = CallStats()
    s.begin("dukaan_dost")
    s.set_channel("phone-616919ff")
    for lang in ("en-IN", "hi-IN", "hi-IN"):
        s.turn(lang)
    s.barge_in()
    s.barge_in()
    s.no_speech()
    s.model_failure()
    r = s.finish("ordered", order_id="20261107-214000-123", total=185, status="confirmed")
    assert r["channel"] == "phone" and r["shop"] == "dukaan_dost"
    assert (r["turns"], r["barge_ins"], r["no_speech"], r["model_failures"]) == (3, 2, 1, 1)
    assert r["language"] == "hi-IN" and r["outcome"] == "ordered"
    assert r["order_id"] == "20261107-214000-123" and r["total"] == 185 and r["status"] == "confirmed"
    assert s.finish("nothing") is None                      # a call whose end is reported twice is saved once


def test_a_browser_node_is_a_browser_call_and_counts_before_begin_are_ignored():
    s = CallStats()
    s.turn("en-IN")
    s.barge_in()                                            # no call open: nothing to count
    s.begin("x")
    s.set_channel("abc123")
    r = s.finish("nothing")
    assert r["channel"] == "browser" and r["turns"] == 0 and r["barge_ins"] == 0


def test_a_new_call_drops_one_whose_end_was_missed():
    s = CallStats()
    s.begin("a")
    s.turn("en-IN")
    s.begin("b")
    r = s.finish("nothing")
    assert r["shop"] == "b" and r["turns"] == 0


def test_the_record_holds_counts_only_no_words_and_no_phone_number():
    s = CallStats()
    s.begin("x")
    s.set_channel("phone-ab12cd34")
    text = json.dumps(s.finish("nothing"))
    assert "07974" not in text and "+91" not in text
    assert set(json.loads(text)) <= {"call_id", "time", "shop", "channel", "seconds", "language", "turns", "barge_ins",
                                      "no_speech", "model_failures", "outcome", "order_id", "total", "status"}


def test_counting_from_several_threads_loses_nothing():
    s = CallStats()
    s.begin("x")
    threads = [threading.Thread(target=lambda: [s.barge_in() for _ in range(200)]) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert s.finish("nothing")["barge_ins"] == 1000


def test_a_call_record_is_saved_and_appears_in_the_dashboard_snapshot(tmp_path):
    s = CallStats()
    s.begin("dukaan_dost")
    s.set_channel("phone-1")
    s.turn("hi-IN")
    record = s.finish("nothing")
    store.write_call("dukaan_dost", record, root=tmp_path)
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["summary"]["calls_total"] == 1 and snap["summary"]["calls_today"] == 1
    call = snap["calls"][0]
    assert call["channel"] == "phone" and call["outcome"] == "nothing" and call["turns"] == 1
    assert snap["orders"] == [] and snap["problems"] == []          # a call is not an order


def test_an_unreadable_call_file_is_reported_not_fatal(tmp_path):
    folder = tmp_path / "dukaan_dost"
    folder.mkdir()
    (folder / "call_broken.json").write_text("{not json", encoding="utf-8")
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["calls"] == [] and any("call_broken" in p for p in snap["problems"])


def test_a_snapshot_with_no_calls_has_an_empty_list(tmp_path):
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["calls"] == [] and snap["summary"]["calls_total"] == 0
