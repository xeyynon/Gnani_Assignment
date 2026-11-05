"""
Tests for the order being taken on a call: the stock check, the quantity rules, the arithmetic, the
sentences the code speaks, and the files written at the end. The money here is the part that must
never be wrong, so these use the real demo shop's stock list.

    python -m pytest tests/test_order_session.py
"""

import json
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import order_session, stock, store  # noqa: E402
from dukaan_dost.order_session import OrderSession  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"
NOW = datetime(2026, 11, 2, 15, 30, tzinfo=store.IST)


@pytest.fixture(scope="module")
def items():
    return stock.load(SHOP)


@pytest.fixture
def session(items):
    return OrderSession("dukaan_dost", items, call_id="t1", now=NOW)


def add(sku, qty):
    return {"op": "add", "sku": sku, "qty": qty}


# ---- arithmetic -------------------------------------------------------------------------------

def test_lines_and_total_are_price_times_quantity(session):
    session.apply([add("SUGAR-1KG", 2), add("OIL-1L", 1), add("MAGGI-70", 4)])
    assert session.total() == 2 * 44 + 165 + 4 * 14 == 309
    rec = session.to_record()
    assert [i["line_total"] for i in rec["items"]] == [88, 165, 56] and rec["total"] == 309


@pytest.mark.parametrize("sku, qty, expected", [
    ("POTATO-1KG", 0.5, 18),       # 17.5 rounds half up
    ("POTATO-1KG", 0.25, 9),       # 8.75
    ("POTATO-1KG", 1.5, 53),       # 52.5
    ("RICE-1KG", 0.75, 45),
    ("ONION-1KG", 25, 1000),
    ("SHAMPOO-SACHET", 24, 48),
])
def test_a_line_is_rounded_to_whole_rupees_half_up(session, sku, qty, expected):
    session.apply([add(sku, qty)])
    assert session.to_record()["items"][0]["line_total"] == expected


def test_the_total_is_the_sum_of_the_rounded_lines(session):
    session.apply([add("POTATO-1KG", 0.5), add("POTATO-1KG", 0)])           # 18, and a refused zero
    session.apply([add("TOMATO-1KG", 0.25)])                                 # 7.5 -> 8
    rec = session.to_record()
    assert sum(i["line_total"] for i in rec["items"]) == rec["total"] == 26


def test_adding_more_of_an_item_increases_its_quantity(session):
    session.apply([add("SUGAR-1KG", 1)])
    result = session.apply([add("SUGAR-1KG", 1.5)])
    assert session.lines["SUGAR-1KG"] == 2.5 and result.changes[0].kind == "updated"
    assert session.total() == 110


def test_set_replaces_the_quantity_and_remove_takes_it_out(session):
    session.apply([add("SUGAR-1KG", 3), add("OIL-1L", 1)])
    session.apply([{"op": "set", "sku": "SUGAR-1KG", "qty": 1}])
    assert session.total() == 44 + 165
    session.apply([{"op": "remove", "sku": "OIL-1L"}])
    assert list(session.lines) == ["SUGAR-1KG"] and session.total() == 44


def test_removing_part_of_a_line_and_removing_what_is_not_there(session):
    session.apply([add("SUGAR-1KG", 3)])
    session.apply([{"op": "remove", "sku": "SUGAR-1KG", "qty": 1}])
    assert session.lines["SUGAR-1KG"] == 2
    result = session.apply([{"op": "remove", "sku": "OIL-1L"}])
    assert result.changes[0].kind == "not_in_order"
    session.apply([{"op": "remove", "sku": "SUGAR-1KG", "qty": 5}])             # more than there is: the line goes
    assert session.is_empty


# ---- what is refused ----------------------------------------------------------------------------

def test_an_unknown_item_is_refused(session):
    result = session.apply([add("DRAGONFRUIT-1KG", 1)])
    assert result.changes[0].kind == "unknown" and session.is_empty


def test_an_item_out_of_stock_is_refused(session):
    result = session.apply([add("PANEER-200", 1)])
    assert result.changes[0].kind == "unavailable" and session.is_empty


@pytest.mark.parametrize("sku, qty", [
    ("SUGAR-1KG", 0.3),            # not a multiple of 0.25
    ("SUGAR-1KG", 26),             # too many kilos
    ("SUGAR-1KG", 0), ("SUGAR-1KG", -1), ("SUGAR-1KG", "abc"), ("SUGAR-1KG", None), ("SUGAR-1KG", True),
    ("SUGAR-1KG", float("nan")), ("SUGAR-1KG", float("inf")),
    ("MAGGI-70", 2.5),             # packets are whole
    ("MAGGI-70", 25),
    ("MAGGI-70", 0.5),
])
def test_a_bad_quantity_is_refused_and_nothing_is_added(session, sku, qty):
    result = session.apply([{"op": "add", "sku": sku, "qty": qty}])
    assert result.changes[0].kind == "bad_qty" and session.is_empty


def test_the_sum_of_two_adds_cannot_pass_the_limit(session):
    session.apply([add("SUGAR-1KG", 20)])
    result = session.apply([add("SUGAR-1KG", 10)])
    assert result.changes[0].kind == "bad_qty" and session.lines["SUGAR-1KG"] == 20


def test_malformed_operations_are_ignored(session):
    result = session.apply(["add sugar", {"op": "explode", "sku": "SUGAR-1KG"}, {"sku": "SUGAR-1KG"}, None, 7])
    assert result.changes == [] and session.is_empty


# ---- payment, customer, delivery -------------------------------------------------------------------

@pytest.mark.parametrize("said, kept", [("cash", "cash"), ("CASH", "cash"), ("cod", "cash"), ("UPI", "upi"),
                                        ("credit", "udhaar"), ("udhaar", "udhaar"), ("bitcoin", None), ("", None)])
def test_payment_words_are_normalised_and_unknown_ones_ignored(session, said, kept):
    session.apply([], payment=said)
    assert session.payment == kept


def test_the_status_follows_the_payment(session):
    session.apply([add("SUGAR-1KG", 1)])
    assert session.status() == "incomplete"
    session.apply([], payment="upi")
    assert session.status() == "confirmed"
    session.apply([], payment="udhaar")
    assert session.status() == "credit_pending"


def test_the_customer_name_is_cleaned(session):
    session.apply([], customer="  Ramesh <script>alert(1)</script> Kumar  ")
    assert "<" not in session.customer and ">" not in session.customer and len(session.customer) <= 40
    session.apply([], customer="రమేష్")
    assert session.customer == "రమేష్"
    session.apply([], customer=12345)
    assert session.customer == "రమేష్"


@pytest.mark.parametrize("said, kept", [("home", "home delivery"), ("pickup", "pickup"), ("Pick up", "pickup"),
                                        ("drone", None)])
def test_delivery_is_normalised(session, said, kept):
    session.apply([], delivery=said)
    assert session.delivery == kept


# ---- what the model is shown --------------------------------------------------------------------------

def test_the_model_sees_the_order_but_no_amounts(session):
    assert session.state_for_model() == "CURRENT ORDER: empty."
    session.apply([add("SUGAR-1KG", 2), add("OIL-1L", 1)], payment="cash", customer="Ramesh")
    state = session.state_for_model()
    assert "SUGAR-1KG Sugar 2 kg" in state and "OIL-1L Sunflower oil 1 litre" in state
    assert "payment: cash" in state and "customer name: Ramesh" in state
    assert not re.search(r"88|165|253|rupee|₹", state)


# ---- what the code says ----------------------------------------------------------------------------------

def test_what_was_added_is_said_with_exact_figures_in_three_languages(session):
    result = session.apply([add("SUGAR-1KG", 2), add("OIL-1L", 1)])
    assert session.changes_text(result.changes, "en-IN") == \
        "Added 2 kilo Sugar 88 rupees, 1 litre Sunflower oil 165 rupees. Total so far 253 rupees."
    assert session.changes_text(result.changes, "hi-IN") == \
        "2 किलो चीनी 88 रुपये, 1 लीटर सूरजमुखी तेल 165 रुपये जोड़ दिया। अभी तक कुल 253 रुपये।"
    assert session.changes_text(result.changes, "te-IN") == \
        "2 కిలో చక్కెర 88 రూపాయలు, 1 లీటర్ సన్‌ఫ్లవర్ నూనె 165 రూపాయలు జోడించాను. ఇప్పటి వరకు మొత్తం 253 రూపాయలు."


def test_count_units_get_plurals_in_english_and_no_unit_word_for_pieces(session):
    result = session.apply([add("MAGGI-70", 4), add("BREAD-400", 1), add("LEMON-1", 3)])
    text = session.changes_text(result.changes, "en-IN")
    assert "4 packets Maggi noodles 56 rupees" in text and "1 Bread 45 rupees" in text and "3 Lemon 15 rupees" in text


def test_an_unknown_language_is_spoken_in_english(session):
    result = session.apply([add("SUGAR-1KG", 1)])
    assert session.changes_text(result.changes, "ta-IN").startswith("Added 1 kilo Sugar 44 rupees")
    assert session.changes_text(result.changes, None).startswith("Added")


def test_refusals_are_spoken_by_name(session):
    result = session.apply([add("PANEER-200", 1), add("SUGAR-1KG", 0.3), add("NOPE", 1)])
    text = session.changes_text(result.changes, "en-IN")
    assert "Paneer is not available today." in text and "quantity for Sugar" in text and "could not find" in text
    assert "Total so far" not in text                       # nothing was added, so no total
    assert "पनीर आज उपलब्ध नहीं है।" in session.changes_text(result.changes, "hi-IN")


def test_the_readback_lists_everything_and_the_total(session):
    session.apply([add("SUGAR-1KG", 2), add("MAGGI-70", 1)])
    assert session.readback("en-IN") == "Your order: 2 kilo Sugar 88 rupees, 1 packet Maggi noodles 14 rupees. Total 102 rupees."
    assert "कुल 102 रुपये।" in session.readback("hi-IN") and "మొత్తం 102 రూపాయలు." in session.readback("te-IN")


def test_the_readback_of_an_empty_order(session):
    assert session.readback("en-IN") == "Nothing in your order yet."


def test_a_quantity_with_a_fraction_is_spoken_plainly(session):
    result = session.apply([add("RICE-1KG", 1.5)])
    assert "1.5 kilo Rice (Sona Masoori)" in session.changes_text(result.changes, "en-IN") or \
           "1.5 kilo Rice" in session.changes_text(result.changes, "en-IN")


# ---- the page and the files ----------------------------------------------------------------------------------

def test_the_call_page_event(session):
    seen = []
    session.listener = seen.append
    session.apply([add("SUGAR-1KG", 2)])
    assert seen == [{"type": "order", "total": 88,
                     "items": [{"name": "Sugar", "qty": 2, "unit": "kg", "line_total": 88}]}]


def test_the_page_is_told_only_about_real_changes_and_a_failing_page_does_not_break_the_call(session):
    seen = []
    session.listener = seen.append
    session.apply([add("PANEER-200", 1)])
    assert seen == []

    def broken(event):
        raise RuntimeError("page closed")
    session.listener = broken
    session.apply([add("SUGAR-1KG", 1)])
    assert session.total() == 44


def test_closing_writes_the_dashboard_file_and_a_readable_copy(session, tmp_path):
    session.apply([add("SUGAR-1KG", 2), add("OIL-1L", 1)], payment="cash", customer="Ramesh", delivery="home",
                  language="hi-IN")
    record = session.close(tmp_path)
    assert record["total"] == 253 and record["status"] == "confirmed"
    saved = json.loads((tmp_path / "dukaan_dost" / "order_t1.json").read_text(encoding="utf-8"))
    assert saved["type"] == "order" and saved["shop"] == "dukaan_dost" and saved["customer"] == "Ramesh"
    assert saved["language"] == "hi-IN" and saved["payment"] == "cash" and saved["delivery"] == "home delivery"
    text = (tmp_path / "dukaan_dost" / "order_t1.txt").read_text(encoding="utf-8")
    assert "Total: 253 rupees" in text and "Sugar" in text and "Status: confirmed" in text
    assert [p.name for p in (tmp_path / "dukaan_dost").glob("order_*.json")] == ["order_t1.json"]


def test_the_dashboard_can_read_what_the_agent_wrote(session, tmp_path):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Anita")
    session.close(tmp_path)
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["problems"] == [] and len(snap["orders"]) == 1
    order = snap["orders"][0]
    assert order["total"] == 88 and order["status"] == "credit_pending" and order["customer"] == "Anita"
    assert order["synthetic"] is False


def test_the_synthetic_flag_comes_from_the_environment(session, tmp_path, monkeypatch):
    monkeypatch.setenv("ORDER_SYNTHETIC", "1")
    session.apply([add("SUGAR-1KG", 1)])
    assert session.close(tmp_path)["synthetic"] is True


def test_an_empty_order_writes_nothing(session, tmp_path):
    assert session.close(tmp_path) is None
    assert not (tmp_path / "dukaan_dost").exists()


def test_a_closed_order_refuses_further_changes_and_closes_once(session, tmp_path):
    session.apply([add("SUGAR-1KG", 1)])
    assert session.close(tmp_path) is not None
    assert session.close(tmp_path) is None
    result = session.apply([add("OIL-1L", 1)])
    assert result.closed and "OIL-1L" not in session.lines


def test_an_order_with_no_payment_is_saved_as_incomplete(session, tmp_path):
    session.apply([add("SUGAR-1KG", 1)])
    assert session.close(tmp_path)["status"] == "incomplete"


def test_two_threads_adding_at_once_do_not_lose_an_update(items):
    s = OrderSession("dukaan_dost", items, now=NOW)
    threads = [threading.Thread(target=lambda: [s.apply([add("MAGGI-70", 1)]) for _ in range(2)]) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert s.lines["MAGGI-70"] == 20 and s.total() == 280


def test_the_call_id_is_a_safe_file_name(items):
    s = OrderSession("dukaan_dost", items, now=NOW)
    assert s.call_id == "20261102-153000-000" and store.ID_RE.match(s.call_id)


def test_prices_are_spoken_from_the_stock_list(session):
    assert session.prices_text(["SUGAR-1KG"], "en-IN") == "Sugar is 44 rupees per kilo."
    assert session.prices_text(["LEMON-1", "MAGGI-70"], "en-IN") ==         "Lemon is 5 rupees each. Maggi noodles is 14 rupees per packet."
    assert session.prices_text(["SUGAR-1KG"], "hi-IN") == "चीनी 44 रुपये प्रति किलो है।"
    assert session.prices_text(["SUGAR-1KG"], "te-IN") == "చక్కెర కిలోకి 44 రూపాయలు."
    assert session.prices_text(["NOPE", ""], "en-IN") == "" and session.prices_text([], "en-IN") == ""
    assert session.prices_text(None, "en-IN") == ""


def test_the_result_says_when_payment_was_chosen_on_this_turn(session):
    assert session.apply([], payment="cash").payment_set is True
    assert session.apply([], payment="cash").payment_set is False          # unchanged
    assert session.apply([], payment="upi").payment_set is True            # changed his mind
    assert session.apply([], payment="bitcoin").payment_set is False


# ---- B-30: the whole order added again on the payment turn ---------------------------------------

def test_re_adding_the_whole_order_on_the_payment_turn_is_ignored(session):
    session.apply([add("SUGAR-1KG", 4), add("OIL-1L", 16)])
    before = session.total()
    result = session.apply([add("SUGAR-1KG", 4), add("OIL-1L", 16)], payment="cash", customer="Ramesh")
    assert session.total() == before and result.changes == [] and session.payment == "cash"


def test_a_real_change_on_the_payment_turn_is_still_applied(session):
    session.apply([add("SUGAR-1KG", 4), add("OIL-1L", 16)])
    session.apply([add("SUGAR-1KG", 1)], payment="cash")                     # "one more sugar, cash"
    assert float(session.lines["SUGAR-1KG"]) == 5


def test_a_partial_repeat_or_a_different_quantity_is_applied(session):
    session.apply([add("SUGAR-1KG", 4), add("OIL-1L", 2)])
    session.apply([add("SUGAR-1KG", 4)], payment="upi")                       # only one of the two lines: a real add
    assert float(session.lines["SUGAR-1KG"]) == 8


def test_the_same_repeat_on_a_turn_without_payment_is_applied(session):
    session.apply([add("SUGAR-1KG", 2)])
    session.apply([add("SUGAR-1KG", 2)])                                      # "two more sugar" is a normal add
    assert float(session.lines["SUGAR-1KG"]) == 4


def test_a_later_payment_change_is_not_a_replay_check(session):
    session.apply([add("SUGAR-1KG", 2)], payment="cash")
    session.apply([add("SUGAR-1KG", 2)], payment="upi")                       # payment was already chosen: not this guard's case
    assert float(session.lines["SUGAR-1KG"]) == 4
