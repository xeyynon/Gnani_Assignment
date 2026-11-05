"""
Tests for the product search (dukaan_dost/product_search.py) and the catalogue modes of the order prompt.

    python -m pytest tests/test_product_search.py
"""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import conversation_manager as cm  # noqa: E402
from dukaan_dost import stock  # noqa: E402
from dukaan_dost.order_session import OrderSession  # noqa: E402
from dukaan_dost.product_search import ProductSearch, normalise  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"


@pytest.fixture(scope="module")
def items():
    return stock.load(SHOP)


@pytest.fixture(scope="module")
def search(items):
    return ProductSearch(items)


def skus(search, text, k=8):
    return [s for s, _ in search.search(text, k)]


# ---- cleaning ---------------------------------------------------------------------------------------------

def test_the_dot_under_a_devanagari_letter_does_not_matter():
    assert normalise("प्याज़") == normalise("प्याज")
    assert normalise("गुड़") == normalise("गुड")


def test_quantities_punctuation_joiners_and_case_are_dropped():
    assert normalise("2.5 KG, Sugar!") == "kg sugar"
    assert normalise("चीनी।") == "चीनी"
    assert normalise("చక్కెర‌") == "చక్కెర"
    assert normalise("") == "" and normalise(None) == ""


# ---- finding products -------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("आधा किलो प्याज और एक किलो आलू चाहिए", {"ONION-1KG", "POTATO-1KG"}),          # no dot under the ज
    ("ఒక కిలో కందిపప్పు మరియు 2 సబ్బులు కావాలి", {"DAL-TOOR-1KG", "SOAP-100"}),     # a Telugu plural
    ("1.5 किलो छीनी चाहिए", {"SUGAR-1KG"}),                                          # a mis-heard cheeni
    ("pyaz aur aloo", {"ONION-1KG", "POTATO-1KG"}),                                  # Latin letters
    ("curd, butter and ghee", {"CURD-400", "BUTTER-100", "GHEE-500"}),
    ("shakkar aur chaval dena", {"SUGAR-1KG", "RICE-1KG"}),                          # spellings in no alias list
    ("a bottle of cold drink and water", {"COLD-750", "WATER-1L"}),
])
def test_the_products_in_a_sentence_are_found(search, text, expected):
    assert expected <= set(skus(search, text))


def test_a_sentence_naming_several_products_does_not_dilute_any_of_them(search):
    found = skus(search, "tamatar pyaz aloo lehsun adrak nimbu", 8)
    for sku in ("TOMATO-1KG", "ONION-1KG", "POTATO-1KG", "GARLIC-250", "GINGER-250", "LEMON-1"):
        assert sku in found


def test_the_best_match_comes_first(search):
    assert skus(search, "ek kilo basmati chawal")[0] == "BASMATI-1KG"
    assert skus(search, "paneer")[0] == "PANEER-200"


def test_results_are_limited_sorted_and_scored(search):
    r = search.search("cheeni namak haldi aur mirch powder jeera", 3)
    assert len(r) <= 3 and [s for _, s in r] == sorted((s for _, s in r), reverse=True)
    assert all(0.3 <= s <= 1.0001 for _, s in r)


def test_nothing_to_search_gives_nothing(search):
    assert search.search("", 5) == [] and search.search("2 kilo please", 5) == [] and search.search("laptop", 5) == []


def test_it_is_fast_enough_to_run_on_every_turn(search):
    import time
    t0 = time.perf_counter()
    for _ in range(20):
        search.search("आधा किलो प्याज और एक किलो आलू चाहिए aur ek packet Maggi", 8)
    assert (time.perf_counter() - t0) / 20 < 0.05                   # well under 50 ms a search


def test_it_is_only_a_candidate_finder_and_can_return_false_matches(search):
    """Documented behaviour: sentences with no product can still return weak matches, so the
    result is offered to the model, never used to add anything to an order."""
    assert isinstance(search.search("cash, my name is Ramesh", 4), list)


def test_the_benchmark_set_stays_covered():
    """A guard on the quality measured in evaluation/retrieval_benchmark.py (top 8 found every item on 76 phrases)."""
    sys.path.insert(0, str(ROOT))
    from evaluation.retrieval_cases import CASES
    s = ProductSearch(stock.load(SHOP))
    asked = hit = 0
    for c in CASES:
        found = set(skus(s, c["text"], 8))
        asked += len(c["expected"])
        hit += sum(1 for e in c["expected"] if e in found)
    assert hit / asked >= 0.97, (hit, asked)


# ---- the catalogue modes of the order prompt -------------------------------------------------------------------

@pytest.fixture
def manager():
    return cm.ConversationManager(SHOP, "test-model", 100, 0.2)


@pytest.fixture
def order(manager):
    return OrderSession("dukaan_dost", manager.stock_items)


def test_a_small_shop_gets_the_whole_catalogue_in_auto_mode(manager, order):
    text = manager.catalogue_for("onion", order)
    assert text.count("\n") == len(manager.stock_items) and text.startswith("CATALOGUE (SKU")


def test_search_mode_sends_only_the_best_matches(manager, order):
    manager.catalogue_mode = "search"
    text = manager.catalogue_for("आधा किलो प्याज और एक किलो आलू", order)
    lines = text.splitlines()[1:]
    assert any(l.startswith("ONION-1KG |") for l in lines) and any(l.startswith("POTATO-1KG |") for l in lines)
    assert len(lines) <= manager.catalogue_candidates and "best match" in text.splitlines()[0]
    assert len(text) < 1500


def test_search_mode_always_includes_what_is_already_in_the_order(manager, order):
    manager.catalogue_mode = "search"
    order.apply([{"op": "add", "sku": "SOAP-100", "qty": 2}])
    text = manager.catalogue_for("tamatar", order)                  # a correction ("make it 3") names nothing
    assert any(l.startswith("SOAP-100 |") for l in text.splitlines()[1:])


def test_full_mode_ignores_the_search(manager, order):
    manager.catalogue_mode = "full"
    assert manager.catalogue_for("onion", order).count("\n") == len(manager.stock_items)


def test_auto_mode_switches_to_search_when_the_catalogue_is_big(manager, order, items):
    big = []
    for i in range(6):                                              # 366 items: every name repeated with a new SKU
        for it in items:
            clone = copy.deepcopy(it)
            clone["sku"] = f"{it['sku']}-C{i}" if i else it["sku"]
            big.append(clone)
    manager.stock_items = big
    manager.product_search = ProductSearch(big)
    full = stock.catalogue_text(big)
    assert len(full) > manager.catalogue_auto_max_chars
    text = manager.catalogue_for("पनीर", OrderSession("dukaan_dost", big))
    assert len(text) < len(full) / 10 and "PANEER-200" in text


def test_the_catalogue_can_be_limited_to_chosen_items(items):
    text = stock.catalogue_text(items, only={"SUGAR-1KG", "PANEER-200"})
    lines = text.splitlines()
    assert len(lines) == 3 and lines[1].startswith("SUGAR-1KG |") or lines[1].startswith("PANEER-200 |")
    assert any(l.endswith("OUT OF STOCK") for l in lines)
