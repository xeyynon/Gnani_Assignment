"""
Tests for keyword retrieval over a shop's knowledge files, in particular that Hindi and Telugu
words are kept whole (Python's \w alone cuts them at their vowel signs).

    python -m pytest tests/test_knowledge_retriever.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import knowledge_retriever as kr  # noqa: E402

ATTA = "## Atta (wheat flour) — आटा — గోధుమ పిండి\nSKU ATTA-5KG | 5 kg bag | 260 rupees\nAlso called: aata, gehu"
SUGAR = "## Sugar — चीनी — చక్కెర\nSKU SUGAR-1KG | 1 kg | 44 rupees\nAlso called: cheeni"
CONFIRM = "## Orders\nOrders are prepared after order confirmation."


@pytest.mark.parametrize("text, words", [
    ("mujhe do kilo आटा chahiye", {"mujhe", "do", "kilo", "आटा", "chahiye"}),
    ("రెండు కిలోల బియ్యం కావాలి", {"రెండు", "కిలోల", "బియ్యం", "కావాలి"}),
    ("Two KG Atta, please!", {"two", "kg", "atta", "please"}),
])
def test_words_in_indian_scripts_are_kept_whole(text, words):
    assert kr._tokens(text) == words


@pytest.mark.parametrize("query, section, expected", [
    ("आटा chahiye", ATTA, 3),                    # Hindi word in the heading: 3
    ("గోధుమ పిండి ఇవ్వండి", ATTA, 6),            # two Telugu words in the heading
    ("atta kitne ka hai", ATTA, 3),
    ("aata", ATTA, 2),                           # only in the "Also called" line: 2
    ("5", ATTA, 1),                              # only in the body: 1
    ("चीनी", ATTA, 0),                           # a different product does not match
    ("चीनी", SUGAR, 3),
    ("confirm", CONFIRM, 0),                     # whole words only: confirm is not confirmation
    ("confirmation", CONFIRM, 1),
])
def test_scoring_matches_whole_words_in_every_script_and_weights_the_name(query, section, expected):
    assert kr._score_section(section, kr._tokens(query)) == expected


def test_a_word_does_not_match_inside_a_longer_one():
    assert kr._score_section("## x\nआटे का भाव", {"आट"}) == 0
    assert kr._score_section("## x\nగోధుమలు", {"గోధుమ"}) == 0


def test_the_right_product_section_comes_back_for_a_hindi_and_a_telugu_request(tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "products_pricing.md").write_text(ATTA + "\n\n" + SUGAR, encoding="utf-8")
    hindi = kr.get_relevant_context(tmp_path, "mujhe चीनी chahiye")
    telugu = kr.get_relevant_context(tmp_path, "గోధుమ పిండి కావాలి")
    assert hindi.startswith("## Sugar") and "Atta" not in hindi.split("\n\n")[0]
    assert telugu.startswith("## Atta")


def test_a_speculative_result_is_reused_when_the_final_transcript_extends_the_partial(tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "products_pricing.md").write_text(ATTA, encoding="utf-8")
    kr.prefetch_relevant_context(tmp_path, "आटा")
    assert "Atta" in kr.get_relevant_context_maybe_cached(tmp_path, "आटा do kilo")


@pytest.mark.parametrize("request_text, first_heading", [
    ("what is the price of ghee?", "## Ghee"),
    ("add one ghee", "## Ghee"),
    ("I want a kilo of dragon fruit and two packets of Parle-G", "## Parle-G biscuits"),
])
def test_everyday_words_do_not_outrank_the_product_asked_for(request_text, first_heading):
    shop = Path(__file__).resolve().parent.parent / "shops" / "dukaan_dost"
    assert kr.get_relevant_context(shop, request_text).startswith(first_heading)


def test_a_message_of_only_everyday_words_does_not_fail(tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "faq.md").write_text("## The price\nthe price is fixed", encoding="utf-8")
    kr.get_relevant_context(tmp_path, "what is the")
    assert kr.get_relevant_context(tmp_path, "") == ""
