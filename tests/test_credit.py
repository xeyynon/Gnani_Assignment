"""
Tests for the udhaar (credit) book: the customer list, finding a customer by a spoken name, limits, the ledger, and
the order flow around credit (ask for a name, approve within the limit, refuse over it, unknown names left to the
shopkeeper, balance enquiries, and settling the ledger when the call ends). The model is replaced by scripted
answers; the customers are the made-up ones in shops/dukaan_dost/customers.json.

    python -m pytest tests/test_credit.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import conversation_manager as cm  # noqa: E402
from dukaan_dost import credit, order_turn, stock, store  # noqa: E402
from dukaan_dost.order_session import OrderSession  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"
NOW = datetime(2026, 11, 3, 12, 0, tzinfo=store.IST)


@pytest.fixture(scope="module")
def items():
    return stock.load(SHOP)


@pytest.fixture
def book(tmp_path):
    return credit.CreditBook("dukaan_dost", credit.load_customers(SHOP), root=tmp_path)


@pytest.fixture
def session(items, book):
    return OrderSession("dukaan_dost", items, call_id="c1", now=NOW, credit=book)


def add(sku, qty):
    return {"op": "add", "sku": sku, "qty": qty}


# ---- the customer list ---------------------------------------------------------------------------------------------

def test_the_shops_customer_list_is_valid():
    customers = credit.load_customers(SHOP)
    assert len(customers) == 15 and len({c["id"] for c in customers}) == 15
    for c in customers:
        assert all(c["name"][lang].strip() for lang in ("en", "hi", "te")) and c["credit_limit"] > 0
        assert 0 <= c["opening_balance"] <= c["credit_limit"]


def test_the_customer_names_are_in_their_own_scripts():
    import re
    for c in credit.load_customers(SHOP):
        assert re.search(r"[ऀ-ॿ]", c["name"]["hi"]) and re.search(r"[ఀ-౿]", c["name"]["te"])


def test_the_customer_file_holds_no_phone_numbers_or_ids():
    text = (SHOP / "customers.json").read_text(encoding="utf-8")
    import re
    assert not re.search(r"\d{8,}", text) and "@" not in text


@pytest.mark.parametrize("change, message", [
    (lambda d: d["customers"][1].update(id=d["customers"][0]["id"]), "repeated"),
    (lambda d: d["customers"][0].update(id="Bad Id"), "bad or repeated"),
    (lambda d: d["customers"][0]["name"].pop("te"), "no te name"),
    (lambda d: d["customers"][0].update(credit_limit=0), "bad limit"),
    (lambda d: d["customers"][0].update(opening_balance=-5), "bad limit"),
])
def test_a_bad_customer_list_is_refused_with_a_reason(tmp_path, change, message):
    data = json.loads((SHOP / "customers.json").read_text(encoding="utf-8"))
    change(data)
    (tmp_path / "customers.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        credit.load_customers(tmp_path)


def test_a_shop_without_customers_has_no_credit_book(tmp_path):
    assert credit.load_customers(tmp_path) == [] and credit.CreditBook.for_shop("x", tmp_path) is None


# ---- the ledger -------------------------------------------------------------------------------------------------------

def test_the_ledger_starts_from_the_opening_balances_and_the_dashboard_can_read_it(book, tmp_path):
    assert book.balance("ramesh") == 400 and book.limit("ramesh") == 2000 and book.balance("venkat") == 0
    ledger = store.read_ledger("dukaan_dost", tmp_path)["customers"]
    assert len(ledger) == 15 and ledger["anita"]["name"] == "Anita" and ledger["anita"]["credit_limit"] == 3000
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["problems"] == [] and len(snap["ledger"]) >= 1


def test_opening_a_book_again_never_resets_balances(book, tmp_path):
    book.record("ramesh", "c9", 100, NOW)
    again = credit.CreditBook("dukaan_dost", credit.load_customers(SHOP), root=tmp_path)
    assert again.balance("ramesh") == 500


def test_a_new_customer_is_added_to_an_existing_ledger(tmp_path):
    first = credit.load_customers(SHOP)[:3]
    credit.CreditBook("dukaan_dost", first, root=tmp_path)
    full = credit.CreditBook("dukaan_dost", credit.load_customers(SHOP), root=tmp_path)
    assert full.balance("mohan") == 1750


def test_recording_an_order_adds_to_the_balance_and_logs_it(book, tmp_path):
    assert book.record("ramesh", "c1", 253, NOW) == 653
    entry = store.read_ledger("dukaan_dost", tmp_path)["customers"]["ramesh"]
    assert entry["balance"] == 653 and entry["last_purchase"] == "2026-11-03"
    assert entry["entries"] == [{"time": NOW.isoformat(), "call_id": "c1", "delta": 253, "note": "order"}]
    with pytest.raises(KeyError):
        book.record("nobody", "c1", 5)


@pytest.mark.parametrize("cid, amount, ok, before, after", [
    ("ramesh", 1600, True, 400, 2000),            # exactly at the limit is allowed
    ("ramesh", 1601, False, 400, 2001),
    ("suresh", 44, True, 450, 494),
    ("suresh", 330, False, 450, 780),
    ("venkat", 0, True, 0, 0),
])
def test_the_limit_check(book, cid, amount, ok, before, after):
    c = book.check(cid, amount)
    assert (c.ok, c.before, c.after) == (ok, before, after) and c.limit == book.limit(cid)


# ---- finding a customer by a spoken name -------------------------------------------------------------------------------

@pytest.mark.parametrize("heard, cid", [
    ("Ramesh", "ramesh"), ("ramesh", "ramesh"), ("RAMESH", "ramesh"), ("Ramesh ji", "ramesh"), ("Ramesh bhai", "ramesh"),
    ("रमेश जी", "ramesh"), ("रमेश भैया", "ramesh"), ("రమేష్ గారు", "ramesh"), ("లక్ష్మి అక్క", "lakshmi"),
    ("Rameshh", "ramesh"), ("रमेश", "ramesh"), ("రమేష్", "ramesh"),
    ("लक्ष्मी", "lakshmi"), ("లక్ష్మి", "lakshmi"), ("Lakshmi", "lakshmi"),
    ("अनीता", "anita"), ("Kavita", "kavitha"), ("श्रीनिवास", "srinivas"), ("Srinivas garu", "srinivas"),
])
def test_a_spoken_name_finds_the_customer_in_any_script(book, heard, cid):
    assert book.find(heard) == cid


@pytest.mark.parametrize("heard", ["Pappu", "Zoya", "", "   ", None, "A", "Mr", "12345", "Ra", "Ramesh Suresh Kiran"])
def test_a_name_that_matches_nobody_clearly_is_unknown(book, heard):
    assert book.find(heard) is None


def test_similar_names_of_different_customers_are_not_confused(book):
    assert book.find("Anita") == "anita" and book.find("Sunita") == "sunita"
    assert book.find("Suresh") == "suresh" and book.find("Ramesh") == "ramesh" and book.find("Rajesh") == "rajesh"


def test_a_close_call_between_two_customers_is_unknown_not_a_guess(tmp_path):
    customers = [
        {"id": "a", "name": {"en": "Mahesh", "hi": "महेश", "te": "మహేష్"}, "credit_limit": 100, "opening_balance": 0},
        {"id": "b", "name": {"en": "Maheshi", "hi": "महेशी", "te": "మహేషి"}, "credit_limit": 100, "opening_balance": 0}]
    close = credit.CreditBook("xx", customers, root=tmp_path)
    assert close.find("Mahesh") is None                          # exact for a, but b is just as near: ambiguous


# ---- credit inside an order -------------------------------------------------------------------------------------------------

def test_choosing_credit_without_a_name_asks_for_the_name(session):
    r = session.apply([add("SUGAR-1KG", 2)], payment="udhaar")
    assert [e["kind"] for e in r.credit_events] == ["need_name"] and session.payment == "udhaar"
    assert session.credit_text(r, "en-IN") == "Please tell me your name so I can check your credit."
    assert session.status() == "credit_pending"


def test_a_known_customer_within_the_limit_is_approved_with_the_balance_spoken(session):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar")
    r = session.apply([], customer="Ramesh")
    assert [e["kind"] for e in r.credit_events] == ["approved"] and session.credit_state == "approved"
    assert session.credit_text(r, "en-IN") == (
        "Ramesh, your credit balance is 400 rupees. This order is 88 rupees, so it will be 488 rupees, within your limit of 2000 rupees.")
    assert (session.balance_before, session.balance_after, session.status()) == (400, 488, "confirmed")


def test_the_same_situation_is_not_announced_twice(session):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    again = session.apply([], customer="Ramesh")
    assert again.credit_events == [] and session.credit_state == "approved"


def test_the_credit_sentences_in_hindi_and_telugu_use_the_customers_own_script(session):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar")
    r = session.apply([], customer="रमेश")
    hi = session.credit_text(r, "hi-IN")
    assert hi.startswith("रमेश, आपका उधार 400 रुपये है") and "488 रुपये" in hi and "2000 रुपये की सीमा" in hi
    te = session.credit_text(r, "te-IN")
    assert te.startswith("రమేష్, మీ అప్పు 400 రూపాయలు") and "488 రూపాయలు" in te


def test_an_order_over_the_limit_is_refused_and_the_caller_must_pay_another_way(session):
    session.apply([add("GHEE-500", 1)], customer="Suresh")                          # 450 owed, limit 500, order 330
    r = session.apply([], payment="udhaar")
    assert [e["kind"] for e in r.credit_events] == ["over_limit"]
    assert session.payment is None and session.credit_state is None and session.status() == "incomplete"
    text = session.credit_text(r, "en-IN")
    assert "this order would take your credit balance to 780 rupees, above your limit of 500 rupees" in text and "cash or UPI" in text
    paid = session.apply([], payment="cash")
    assert session.payment == "cash" and paid.payment_set and session.status() == "confirmed"


def test_adding_items_after_approval_can_push_the_order_over_the_limit(session):
    session.apply([add("SUGAR-1KG", 1)], payment="udhaar", customer="Suresh")        # 450 + 44 = 494, limit 500: approved
    assert session.credit_state == "approved"
    r = session.apply([add("SUGAR-1KG", 1)])                                          # 450 + 88 = 538: over
    assert [e["kind"] for e in r.credit_events] == ["over_limit"] and session.payment is None


def test_removing_items_does_not_reannounce_unless_the_situation_changed(session):
    session.apply([add("SUGAR-1KG", 4)], payment="udhaar", customer="Ramesh")
    r = session.apply([{"op": "remove", "sku": "SUGAR-1KG", "qty": 1}])
    assert [e["kind"] for e in r.credit_events] == ["approved"]                       # the total changed, so the figures did


def test_an_unknown_name_leaves_the_credit_to_the_shopkeeper(session):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar")
    r = session.apply([], customer="Pappu")
    assert [e["kind"] for e in r.credit_events] == ["unknown"] and session.credit_state == "unknown"
    assert session.credit_text(r, "en-IN") == "I could not find you in the credit book."
    assert session.status() == "credit_pending"


def test_paying_in_cash_never_touches_the_credit_book(session, book):
    session.apply([add("SUGAR-1KG", 2)], payment="cash", customer="Ramesh")
    assert session.credit_state is None and session.credit_id == "ramesh"
    session.close()
    assert book.balance("ramesh") == 400


def test_a_shop_with_no_credit_book_keeps_the_old_behaviour(items):
    plain = OrderSession("dukaan_dost", items, now=NOW)
    r = plain.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    assert r.credit_events == [] and plain.status() == "credit_pending" and plain.credit_text(r, "en-IN") == ""


# ---- balance enquiries --------------------------------------------------------------------------------------------------------

def test_a_balance_enquiry_with_a_name_answers_at_once(session):
    r = session.apply([], customer="Ramesh", balance_query=True)
    assert [e["kind"] for e in r.credit_events] == ["balance"]
    assert session.credit_text(r, "en-IN") == "Ramesh, you owe 400 rupees. Your credit limit is 2000 rupees."


def test_a_balance_enquiry_without_a_name_asks_then_answers_on_the_next_turn(session):
    asked = session.apply([], balance_query=True)
    assert [e["kind"] for e in asked.credit_events] == ["need_name"]
    answered = session.apply([], customer="रमेश")
    assert [e["kind"] for e in answered.credit_events] == ["balance"]
    assert session.credit_text(answered, "hi-IN") == "रमेश, आपका 400 रुपये उधार बाकी है। आपकी उधार सीमा 2000 रुपये है।"
    assert session.apply([], customer="रमेश").credit_events == []                      # answered once, not repeated


def test_a_customer_who_owes_nothing_is_told_so(session):
    r = session.apply([], customer="Venkat", balance_query=True)
    assert session.credit_text(r, "en-IN") == "Venkat, you owe nothing right now. Your credit limit is 2000 rupees."


def test_a_balance_enquiry_for_an_unknown_name_says_so(session):
    r = session.apply([], customer="Pappu", balance_query=True)
    assert [e["kind"] for e in r.credit_events] == ["balance_unknown"]


# ---- settling at the end of the call ---------------------------------------------------------------------------------------------

def test_the_ledger_and_the_order_file_agree_when_the_call_ends(session, book, tmp_path):
    session.apply([add("SUGAR-1KG", 2), add("OIL-1L", 1)], payment="udhaar", customer="Ramesh")   # 253
    record = session.close(tmp_path)
    assert record["status"] == "confirmed" and record["customer"] == "Ramesh" and record["payment"] == "udhaar"
    assert (record["balance_before"], record["balance_after"]) == (400, 653)
    assert book.balance("ramesh") == 653
    saved = json.loads((tmp_path / "dukaan_dost" / "order_c1.json").read_text(encoding="utf-8"))
    assert saved["balance_after"] == 653
    assert store.read_ledger("dukaan_dost", tmp_path)["customers"]["ramesh"]["entries"][-1]["call_id"] == "c1"


def test_closing_twice_does_not_charge_twice(session, book, tmp_path):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    session.close(tmp_path)
    assert session.close(tmp_path) is None and book.balance("ramesh") == 488


def test_an_order_that_stopped_fitting_while_the_call_ran_is_left_pending_not_charged(session, book, tmp_path):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Suresh")                      # 450 + 88 = 538 > 500? over
    assert session.credit_state is None                                                              # already refused
    ok = OrderSession("dukaan_dost", stock.load(SHOP), call_id="c2", now=NOW, credit=book)
    ok.apply([add("SUGAR-1KG", 1)], payment="udhaar", customer="Suresh")                            # 494: approved
    book.record("suresh", "other-call", 40, NOW)                                                     # another call used 40 meanwhile
    record = ok.close(tmp_path)
    assert record["status"] == "credit_pending" and record["balance_after"] is None and book.balance("suresh") == 490


def test_a_ledger_that_cannot_be_written_does_not_lose_the_order(session, book, tmp_path, monkeypatch):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(book, "record", boom)
    record = session.close(tmp_path)
    assert record is not None and record["status"] == "credit_pending" and (tmp_path / "dukaan_dost" / "order_c1.json").exists()


def test_the_customer_name_in_the_record_is_the_books_not_the_heard_spelling(session, tmp_path):
    session.apply([add("SUGAR-1KG", 1)], payment="udhaar", customer="रमेश जी")
    assert session.close(tmp_path)["customer"] == "Ramesh"


def test_the_dashboard_shows_the_new_balance(session, tmp_path):
    session.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    session.close(tmp_path)
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    rows = {r["name"]: r for r in snap["ledger"]}
    assert rows["Ramesh"]["balance"] == 488 and snap["problems"] == []


# ---- reading the note and speaking the reply -------------------------------------------------------------------------------------

def note(ops=(), say="", payment=None, name=None, balance=False, finish=False):
    return json.dumps({"ops": list(ops), "payment": payment, "customer_name": name, "delivery": None, "finish": finish,
                       "balance_query": balance, "price_of": [], "not_sold": [], "say": say})


def test_the_plan_reads_the_balance_flag_strictly():
    assert order_turn.parse_plan(note(balance=True)).balance_query is True
    assert order_turn.parse_plan('{"balance_query": "true"}').balance_query is False
    assert "balance_query" in order_turn.SCHEMA["properties"] and "balance_query" in order_turn.SCHEMA["required"]
    assert "balance_query" in order_turn.prompt_section() and "owe" in order_turn.prompt_section()


def reply(session, raw, language="en-IN", closing="CLOSING."):
    plan = order_turn.parse_plan(raw)
    result = session.apply(plan.ops, plan.payment, plan.customer_name, plan.delivery, plan.finish,
                           language=language, balance_query=plan.balance_query)
    return order_turn.compose(plan, result, session, language, closing=closing)


def test_choosing_credit_asks_for_the_name_and_does_not_close_the_order(session):
    assert reply(session, note([add("SUGAR-1KG", 2)], payment="udhaar")) == (
        "Added 2 kilo Sugar 88 rupees. Total so far 88 rupees. Please tell me your name so I can check your credit.")


def test_giving_the_name_approves_and_closes_the_order(session):
    reply(session, note([add("SUGAR-1KG", 2)], payment="udhaar"))
    assert reply(session, note(name="Ramesh")) == (
        "Ramesh, your credit balance is 400 rupees. This order is 88 rupees, so it will be 488 rupees, within your limit of 2000 rupees. CLOSING.")


def test_credit_over_the_limit_is_explained_and_the_order_stays_open(session):
    reply(session, note([add("GHEE-500", 1)], name="Suresh"))
    text = reply(session, note(payment="udhaar"))
    assert "above your limit of 500 rupees" in text and "CLOSING." not in text and "Anything else" not in text


def test_an_unknown_name_is_told_and_the_shopkeeper_closing_follows(session):
    reply(session, note([add("SUGAR-1KG", 2)], payment="udhaar"))
    assert reply(session, note(name="Pappu"), closing="The shopkeeper will confirm.") == (
        "I could not find you in the credit book. The shopkeeper will confirm.")


def test_a_balance_question_is_answered_and_the_follow_up_question_added(session):
    assert reply(session, note(name="Ramesh", balance=True)) == (
        "Ramesh, you owe 400 rupees. Your credit limit is 2000 rupees. Anything else?")


def test_that_is_all_with_credit_pending_a_name_reads_the_order_then_asks_the_name(session):
    session.apply([add("SUGAR-1KG", 2)])
    text = reply(session, note(payment="udhaar", finish=True))
    assert text.startswith("Your order: 2 kilo Sugar 88 rupees. Total 88 rupees.") and text.endswith("check your credit.")


# ---- through the conversation manager ----------------------------------------------------------------------------------------------

class Scripted:
    def __init__(self, *answers):
        self.answers = list(answers)

    def __call__(self, model, messages, max_tokens, temperature, schema=None):
        return self.answers.pop(0)


def test_a_whole_credit_call_through_the_manager(items, book, tmp_path, monkeypatch):
    manager = cm.ConversationManager(SHOP, "test-model", 100, 0.2)
    monkeypatch.setattr(cm, "gemini_ask_json", Scripted(
        note([add("SUGAR-1KG", 2)]), note(finish=True), note(payment="udhaar"), note(name="Ramesh")))
    order = OrderSession("dukaan_dost", items, call_id="m1", now=NOW, credit=book)
    said = [" ".join(s for s, _ in manager.handle_turn_streaming(t, [], "", "en-IN", order=order))
            for t in ("do kilo cheeni", "bas itna hi", "udhaar pe", "Ramesh")]
    assert said[2].endswith("Please tell me your name so I can check your credit.")
    assert said[3].startswith("Ramesh, your credit balance is 400 rupees.") and manager.fallback_messages["en-in"] not in said[3]
    assert "45 minutes" in said[3]                        # the ordinary closing, not the "shopkeeper will confirm" one
    record = order.close(tmp_path)
    assert record["status"] == "confirmed" and record["balance_after"] == 488 and book.balance("ramesh") == 488


# ---- the call's lifecycle in the main program --------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


def test_a_call_gets_the_shops_credit_book_and_settles_it_at_hang_up(app, monkeypatch, tmp_path):
    monkeypatch.setattr(store, "ORDERS_DIR", tmp_path)
    app._finish_order("setup")
    try:
        app._set_active_shop()
        assert app._order is not None and app._order.credit is not None
        app._order.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
        app._clear_history("call ended")
        ledger = store.read_ledger("dukaan_dost", tmp_path)["customers"]
        assert ledger["ramesh"]["balance"] == 488
        assert len(list((tmp_path / "dukaan_dost").glob("order_*.json"))) == 1
    finally:
        app._finish_order("teardown")


def test_a_broken_customer_list_does_not_stop_orders(app, monkeypatch, tmp_path):
    monkeypatch.setattr(store, "ORDERS_DIR", tmp_path)
    monkeypatch.setattr(app._credit.CreditBook, "for_shop", classmethod(lambda cls, *a, **k: (_ for _ in ()).throw(ValueError("bad"))))
    app._finish_order("setup")
    try:
        app._set_active_shop()
        assert app._order is not None and app._order.credit is None
    finally:
        app._finish_order("teardown")


# ---- bug hunt of 2026-11-05: the ledger must never be silently reset, charges follow the order file -------------------

def test_a_ledger_that_cannot_be_read_is_never_replaced_by_opening_balances(tmp_path):
    first = credit.CreditBook("dukaan_dost", credit.load_customers(SHOP), root=tmp_path)
    first.record("ramesh", "c1", 1500, NOW)
    path = tmp_path / "dukaan_dost" / "ledger.json"
    path.write_text(path.read_text(encoding="utf-8")[:60], encoding="utf-8")           # cut in half: not valid JSON
    damaged = path.read_text(encoding="utf-8")
    with pytest.raises(store.LedgerUnreadable):
        credit.CreditBook("dukaan_dost", credit.load_customers(SHOP), root=tmp_path)
    assert path.read_text(encoding="utf-8") == damaged                                  # nothing was overwritten


def test_a_ledger_that_goes_bad_during_a_call_leaves_credit_to_the_shopkeeper(items, book, tmp_path):
    s = OrderSession("dukaan_dost", items, call_id="c2", now=NOW, credit=book)
    s.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    assert s.credit_state == "approved"
    (tmp_path / "dukaan_dost" / "ledger.json").write_text("{not json", encoding="utf-8")
    again = s.apply([add("SUGAR-1KG", 1)])
    assert [e["kind"] for e in again.credit_events] == ["unknown"] and s.credit_state == "unknown"
    s.close(tmp_path)
    order = json.loads(next((tmp_path / "dukaan_dost").glob("order_*.json")).read_text(encoding="utf-8"))
    assert order["status"] == "credit_pending"
    assert (tmp_path / "dukaan_dost" / "ledger.json").read_text(encoding="utf-8") == "{not json"


def test_a_missing_ledger_is_a_new_one_seeded_from_the_customer_list(tmp_path):
    book = credit.CreditBook("dukaan_dost", credit.load_customers(SHOP), root=tmp_path)
    assert book.balance("ramesh") == 400


def test_a_failed_order_write_never_charges_the_customer(items, book, tmp_path, monkeypatch):
    s = OrderSession("dukaan_dost", items, call_id="c3", now=NOW, credit=book)
    s.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    before = book.balance("ramesh")
    monkeypatch.setattr(store, "write_order", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        s.close(tmp_path)
    assert book.balance("ramesh") == before


def test_a_failed_ledger_write_rewrites_the_order_as_pending(items, book, tmp_path, monkeypatch):
    s = OrderSession("dukaan_dost", items, call_id="c4", now=NOW, credit=book)
    s.apply([add("SUGAR-1KG", 2)], payment="udhaar", customer="Ramesh")
    monkeypatch.setattr(book, "record", lambda *a, **k: (_ for _ in ()).throw(OSError("locked")))
    s.close(tmp_path)
    order = json.loads(next((tmp_path / "dukaan_dost").glob("order_*.json")).read_text(encoding="utf-8"))
    assert order["status"] == "credit_pending" and order.get("balance_after") is None


@pytest.mark.parametrize("heard", ["Venkatesh", "Mohana Rao"])
def test_a_longer_name_that_only_begins_with_a_known_one_is_not_that_customer(book, heard):
    assert book.find(heard) is None


def test_a_one_letter_difference_still_matches(book):
    assert book.find("Rameshh") == "ramesh"


def test_a_file_lock_on_the_ledger_is_waited_out(tmp_path, monkeypatch):
    real = store.os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] < 3:
            raise PermissionError(13, "Access is denied")
        return real(src, dst)

    monkeypatch.setattr(store.os, "replace", flaky)
    store.write_ledger("dukaan_dost", {"customers": {"x": {"balance": 1}}}, tmp_path)
    assert calls["n"] == 3 and store.read_ledger("dukaan_dost", tmp_path)["customers"]["x"]["balance"] == 1
