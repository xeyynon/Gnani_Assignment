"""
Tests for the reply splitter that cuts a streamed answer into speakable sentences. Each clip is
spoken separately with a listening pause between clips, so a bad cut is audible.

    python -m pytest tests/test_sentence_split.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost.conversation_manager import next_sentence  # noqa: E402


def split_all(text, chunk=None):
    """What the streaming loop yields for `text`, optionally arriving `chunk` characters at a time."""
    out, buf = [], ""
    pieces = [text] if chunk is None else [text[i:i + chunk] for i in range(0, len(text), chunk)]
    for piece in pieces:
        buf += piece
        while True:
            found = next_sentence(buf)
            if found is None:
                break
            s, buf = found
            out.append(s)
    if buf.strip():
        out.append(buf.strip())
    return out


@pytest.mark.parametrize("text, expected", [
    ("Atta ka rate Rs. 260 hai. Aur kuch chahiye?", ["Atta ka rate Rs. 260 hai.", "Aur kuch chahiye?"]),
    ("Total Rs. 45.50 hua. Theek hai?", ["Total Rs. 45.50 hua.", "Theek hai?"]),
    ("Aapka order 2 kg atta, 1.5 kg chini. Confirm?", ["Aapka order 2 kg atta, 1.5 kg chini.", "Confirm?"]),
    ("Mr. Sharma ka order ready hai. Dhanyavaad.", ["Mr. Sharma ka order ready hai.", "Dhanyavaad."]),
    ("दो किलो आटा जोड़ दिया। और कुछ चाहिए?", ["दो किलो आटा जोड़ दिया।", "और कुछ चाहिए?"]),
    ("Done! Anything else? Say yes or no.", ["Done! Anything else?", "Say yes or no."]),
])
def test_sentences_are_cut_where_a_listener_expects(text, expected):
    assert split_all(text) == expected


def test_a_short_opening_is_merged_into_the_next_sentence():
    assert split_all("Ji. Do kilo atta add kar diya.") == ["Ji. Do kilo atta add kar diya."]


def test_a_short_reply_on_its_own_is_still_spoken():
    assert split_all("Ji.") == ["Ji."] and split_all("Haan") == ["Haan"]


def test_a_price_is_never_split_from_its_currency_word():
    for text in ("Rs. 260", "Rs.260 hai", "RS. 260 total hua."):
        assert len(split_all(text + " Aur kuch?")) <= 2
        assert split_all(text + " Aur kuch?")[0].lower().startswith(text.lower().split()[0])


def test_the_result_does_not_depend_on_how_the_text_arrives():
    text = "Atta ka rate Rs. 260 hai. Maggi Rs. 14 ka hai. Total 1.5 kg hua. Aur kuch chahiye?"
    whole = split_all(text)
    assert len(whole) == 4
    for size in (1, 2, 3, 5, 7, 11):
        assert split_all(text, chunk=size) == whole


def test_an_abbreviation_at_the_end_of_the_buffer_waits_for_more_text():
    assert next_sentence("Atta ka rate Rs. ") is None
    assert next_sentence("Atta ka rate Rs. 260 hai. Aur") == ("Atta ka rate Rs. 260 hai.", "Aur")


def test_nothing_finished_means_nothing_yielded():
    assert next_sentence("Do kilo atta") is None
    assert next_sentence("") is None
