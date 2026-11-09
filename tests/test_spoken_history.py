"""
Tests for keeping the history honest when a caller interrupts a reply
(dukaan_dost/spoken_history.py and its hooks in app.py).

    python -m pytest tests/test_spoken_history.py
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost.spoken_history import SpokenTracker  # noqa: E402


def make_turn(tracker, reply_id, sentences_and_clips, history=None):
    """Queue a reply the way the processor does, and write its history entries."""
    history = [] if history is None else history
    for sentence, n in sentences_and_clips:
        tracker.planned(reply_id, sentence, n)
    full = " ".join(s for s, _ in sentences_and_clips)
    user, assistant = {"role": "user", "content": "order"}, {"role": "assistant", "content": full}
    history += [user, assistant]
    tracker.register_entry(reply_id, user, assistant)
    return history, user, assistant


def play(tracker, reply_id, n_clips):
    for _ in range(n_clips):
        tracker.clip_finished(reply_id)


PLAN = [("Atta add kar diya.", 2), ("Chini add kar di.", 2), ("Aur kuch chahiye?", 1)]


def test_a_reply_played_in_full_is_left_alone():
    t = SpokenTracker()
    history, _, assistant = make_turn(t, 1, PLAN)
    play(t, 1, 5)
    assert t.trim_after_interrupt(1, history) == "Atta add kar diya. Chini add kar di. Aur kuch chahiye?"
    assert assistant["content"] == "Atta add kar diya. Chini add kar di. Aur kuch chahiye?"


def test_an_interrupted_reply_keeps_only_the_sentences_that_finished():
    t = SpokenTracker()
    history, _, assistant = make_turn(t, 1, PLAN)
    play(t, 1, 2)                                   # the first sentence's two clips finished
    assert t.trim_after_interrupt(1, history) == "Atta add kar diya."
    assert assistant["content"] == "Atta add kar diya."
    assert len(history) == 2


def test_a_sentence_cut_off_part_way_counts_as_not_heard():
    t = SpokenTracker()
    history, _, assistant = make_turn(t, 1, PLAN)
    play(t, 1, 3)                                   # first sentence done, second only half played
    assert t.trim_after_interrupt(1, history) == "Atta add kar diya."
    assert "Chini" not in assistant["content"]


def test_nothing_heard_removes_the_turn_and_keeps_the_history_alternating():
    t = SpokenTracker()
    history = [{"role": "user", "content": "namaste"}, {"role": "assistant", "content": "Namaste ji."}]
    make_turn(t, 2, PLAN, history)
    assert t.trim_after_interrupt(2, history) == ""
    assert history == [{"role": "user", "content": "namaste"}, {"role": "assistant", "content": "Namaste ji."}]


def test_a_reply_with_no_history_entry_yet_reports_none():
    t = SpokenTracker()
    t.planned(3, "Hello there.", 1)
    assert t.trim_after_interrupt(3, []) is None


def test_trimming_twice_gives_the_same_answer():
    t = SpokenTracker()
    history, _, assistant = make_turn(t, 1, PLAN)
    play(t, 1, 2)
    t.trim_after_interrupt(1, history)
    t.trim_after_interrupt(1, history)
    assert assistant["content"] == "Atta add kar diya." and len(history) == 2


def test_an_entry_that_was_already_cleared_is_not_touched():
    t = SpokenTracker()
    history, _, _ = make_turn(t, 1, PLAN)
    history.clear()                                  # a new call cleared the history
    assert t.trim_after_interrupt(1, history) is None


def test_clips_of_other_replies_do_not_count():
    t = SpokenTracker()
    history, _, _ = make_turn(t, 1, PLAN)
    play(t, 99, 10)
    assert t.heard_text(1) == ""


def test_a_sentence_with_no_audio_is_not_recorded():
    t = SpokenTracker()
    t.planned(1, "Nothing was synthesised.", 0)
    assert t.heard_text(1) == ""


def test_forget_clears_everything():
    t = SpokenTracker()
    history, _, _ = make_turn(t, 1, PLAN)
    play(t, 1, 5)
    t.forget()
    assert t.heard_text(1) == "" and t.trim_after_interrupt(1, history) is None


def test_old_replies_are_forgotten_so_memory_stays_bounded():
    t = SpokenTracker()
    for i in range(200):
        t.planned(i, f"sentence {i}", 1)
    assert len(t._plan) <= 64 and 199 in t._plan and 0 not in t._plan


# ---- the hooks in app.py ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


def test_the_app_trims_its_own_history_after_an_interruption(app):
    app._clear_history("test")
    with app._hist_lock:
        make_turn(app._spoken, 7, PLAN, app._history)
    play(app._spoken, 7, 2)
    app._trim_history_for_interrupt(7)
    assert [h["content"] for h in app._history if h["role"] == "assistant"] == ["Atta add kar diya."]
    app._clear_history("test done")


def test_a_new_call_forgets_what_was_queued(app):
    with app._hist_lock:
        make_turn(app._spoken, 8, PLAN, app._history)
    app._clear_history("test")
    assert app._spoken.heard_text(8) == "" and app._history == []


def test_the_playback_and_processor_threads_are_wired_to_the_tracker():
    """The threads cannot be run here, so check the hooks exist (a guard against them being edited away)."""
    source = (ROOT / "dukaan_dost" / "app.py").read_text(encoding="utf-8")
    calls = re.findall(r"^\s+_trim_history_for_interrupt\(reply_id\)", source, re.MULTILINE)
    assert len(calls) == 4                                                    # one per place a reply is abandoned (the last: held back for a caller mid-sentence)
    assert source.count("_spoken.clip_finished(reply_id)") == 1
    assert len(re.findall(r"_spoken\.planned\(reply_id, ", source)) == 2     # the sentence and the fallback
    assert "_spoken.register_entry(reply_id," in source
