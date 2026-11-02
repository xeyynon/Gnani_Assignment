"""
Tests for the demo shop's content (shops/dukaan_dost) and the stock-list tooling.

    python -m pytest tests/test_shop_dukaan_dost.py
"""

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import knowledge_retriever, stock  # noqa: E402
from dukaan_dost.conversation_manager import ConversationManager  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"


@pytest.fixture(scope="module")
def items():
    return stock.load(SHOP)


# ---- the stock list -------------------------------------------------------------------------

def test_the_stock_list_is_valid_and_about_sixty_items(items):
    assert 55 <= len(items) <= 70
    assert len({it["sku"] for it in items}) == len(items)


def test_every_item_has_a_name_in_its_own_script(items):
    devanagari, telugu = re.compile(r"[ऀ-ॿ]"), re.compile(r"[ఀ-౿]")
    for it in items:
        assert devanagari.search(it["name"]["hi"]), it["sku"]
        assert telugu.search(it["name"]["te"]), it["sku"]


def test_a_few_items_are_out_of_stock_so_that_case_can_be_tested(items):
    out = {it["sku"] for it in items if not it["in_stock"]}
    assert 1 <= len(out) <= 4 and "PANEER-200" in out


def test_the_items_the_demo_data_uses_exist_with_the_same_prices(items):
    known = stock.by_sku(items)
    for sku, price in (("ATTA-5KG", 260), ("RICE-1KG", 60), ("OIL-1L", 165), ("DAL-TOOR-1KG", 145),
                       ("MAGGI-70", 14), ("SUGAR-1KG", 44), ("SOAP-100", 38), ("BREAD-400", 45)):
        assert known[sku]["price"] == price


@pytest.mark.parametrize("change, message", [
    (lambda d: d[1].update(sku=d[0]["sku"]), "duplicate sku"),
    (lambda d: d[0].update(unit="barrel"), "unit"),
    (lambda d: d[0].update(price=0), "price"),
    (lambda d: d[0].update(price="40"), "price"),
    (lambda d: d[0]["name"].pop("te"), "te name"),
    (lambda d: d[0].update(aliases=[]), "alias"),
    (lambda d: d[0].update(in_stock="yes"), "in_stock"),
    (lambda d: d[0].update(sku="atta 5kg"), "sku"),
])
def test_a_bad_stock_list_is_rejected_with_a_reason(items, change, message):
    broken = copy.deepcopy(items)
    change(broken)
    problems = stock.validate(broken)
    assert problems and any(message in p for p in problems)


# ---- the generated knowledge file -----------------------------------------------------------------

def test_products_pricing_md_matches_stock_json(items):
    current = (SHOP / "knowledge" / "products_pricing.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert current == stock.render_products_md(items), \
        "run: python scripts/build_shop_knowledge.py shops/dukaan_dost"


def test_the_build_script_check_mode_passes_and_fails_correctly(tmp_path, items):
    script = str(ROOT / "scripts" / "build_shop_knowledge.py")
    ok = subprocess.run([sys.executable, script, str(SHOP), "--check"],
                        capture_output=True, text=True, encoding="utf-8")
    assert ok.returncode == 0, ok.stderr
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "stock.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    (tmp_path / "knowledge" / "products_pricing.md").write_text("stale", encoding="utf-8")
    bad = subprocess.run([sys.executable, script, str(tmp_path), "--check"],
                         capture_output=True, text=True, encoding="utf-8")
    assert bad.returncode == 1 and "out of date" in bad.stderr


def test_an_out_of_stock_item_says_so_in_the_text_the_model_reads(items):
    md = stock.render_products_md(items)
    paneer = md.split("## Paneer")[1].split("##")[0]
    assert "OUT OF STOCK" in paneer and "in stock" not in paneer.replace("OUT OF STOCK", "")


def test_keyterms_are_ascii_unique_and_within_the_prisma_cap(items):
    terms = stock.keyterms(items)
    assert 100 < len(terms) <= 200
    assert all(t.isascii() and "," not in t and len(t) >= 3 for t in terms)
    assert len({t.lower() for t in terms}) == len(terms)
    for brand in ("Maggi noodles", "Amul butter", "Parle-G biscuits"):
        assert brand in terms
    # no product is dropped by the cap: every item's main name is in
    for it in items:
        main = re.sub(r"\s*\(.*?\)", "", it["name"]["en"]).strip()
        assert main in terms or len(main) < 3


# ---- the shop folder loads and answers retrieval ---------------------------------------------------

def test_the_shop_has_every_file_the_agent_reads():
    assert (SHOP / "config.yaml").is_file() and (SHOP / "knowledge" / "core" / "always_on.md").is_file()
    for name in knowledge_retriever.KNOWLEDGE_FILES:
        assert (SHOP / "knowledge" / name).is_file(), name


def test_the_conversation_manager_accepts_the_shop_config():
    mgr = ConversationManager(SHOP, "test-model", 200, 0.3)
    assert set(mgr.fallback_messages) == {"en-in", "hi-in", "te-in"}
    assert "Never invent an item" in mgr.base_prompt and len(mgr.base_prompt) < 4000
    assert mgr.core_context.strip()


@pytest.mark.parametrize("request_text, first_heading", [
    ("mujhe do kilo चीनी chahiye", "## Sugar"),
    ("గోధుమ పిండి కావాలి", "## Atta"),
    ("one packet Maggi please", "## Maggi noodles"),
    ("amul butter hai kya", "## Amul butter"),
    ("तुअर दाल", "## Toor dal"),
    ("కందిపప్పు ఎంత", "## Toor dal"),
])
def test_a_request_in_any_of_the_three_languages_finds_its_product(request_text, first_heading):
    context = knowledge_retriever.get_relevant_context(SHOP, request_text)
    assert context.startswith(first_heading), context[:120]


def test_asking_for_an_out_of_stock_item_returns_the_out_of_stock_note():
    context = knowledge_retriever.get_relevant_context(SHOP, "paneer chahiye")
    assert "## Paneer" in context and "OUT OF STOCK" in context


def test_the_retrieved_context_stays_within_its_budget():
    for text in ("rice dal oil sugar atta chawal", "delivery payment upi credit udhaar", "पनीर"):
        assert len(knowledge_retriever.get_relevant_context(SHOP, text)) <= knowledge_retriever.MAX_CONTEXT_CHARS


def test_payment_and_delivery_questions_find_their_answers():
    assert "dukaandost.demo@upi" in knowledge_retriever.get_relevant_context(SHOP, "upi se payment kar sakte hain")
    assert "3 kilometres" in knowledge_retriever.get_relevant_context(SHOP, "home delivery hoga kya")


# ---- the synthetic-data rule ----------------------------------------------------------------------

def test_the_shop_files_contain_no_phone_numbers_emails_or_ids():
    for path in SHOP.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"(?<!\d)\d{10}(?!\d)", text), path          # a phone-number-sized run
            assert not re.search(r"[\w.]+@(?!upi\b)[\w.]+\.\w+", text), path   # an email address
            assert not re.search(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)", text), path   # an Aadhaar-shaped number


# ---- the product names reach the speech recogniser --------------------------------------------------

@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


def test_a_call_gives_the_shops_product_names_to_the_recogniser(app, monkeypatch):
    given = []
    monkeypatch.setattr(app, "_set_stt_keyterms", lambda terms: given.append(list(terms)) or len(terms))
    app._boost_product_names("dukaan_dost")
    assert len(given[0]) == 200 and "Maggi noodles" in given[0]


def test_a_shop_without_a_stock_list_just_gets_no_boosting(app, monkeypatch, tmp_path):
    given = []
    monkeypatch.setattr(app, "_set_stt_keyterms", lambda terms: given.append(list(terms)) or len(terms))
    monkeypatch.setattr(app._shops, "shop_dir", lambda name, root=None: tmp_path)
    app._boost_product_names("whatever")
    assert given == [[]]


def test_a_broken_stock_list_does_not_stop_the_call(app, monkeypatch, tmp_path):
    (tmp_path / "stock.json").write_text('{"items": [{"sku": "x"}]}', encoding="utf-8")
    given = []
    monkeypatch.setattr(app, "_set_stt_keyterms", lambda terms: given.append(list(terms)) or len(terms))
    monkeypatch.setattr(app._shops, "shop_dir", lambda name, root=None: tmp_path)
    app._boost_product_names("whatever")
    assert given == [[]]
