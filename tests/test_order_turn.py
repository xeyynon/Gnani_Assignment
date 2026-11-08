"""
Tests for one turn of an order call: reading the model's JSON, building the spoken reply, and a
whole scripted conversation through the real shop (the model is replaced by scripted answers).

The rule under test: on any turn that touches the order, the CODE says everything (the changes, the
prices, the read-back, the follow-up question) and the model's own words are not used. They are used
only when nothing about the order happened.

    python -m pytest tests/test_order_turn.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import conversation_manager as cm  # noqa: E402
from dukaan_dost import order_turn, stock, store  # noqa: E402
from dukaan_dost.order_session import OrderSession  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"
NOW = datetime(2026, 11, 2, 15, 30, tzinfo=store.IST)


@pytest.fixture(scope="module")
def items():
    return stock.load(SHOP)


@pytest.fixture
def session(items):
    return OrderSession("dukaan_dost", items, call_id="t1", now=NOW)


def note(ops=(), say="", payment=None, name=None, delivery=None, finish=False, price_of=(), not_sold=()):
    return json.dumps({"ops": list(ops), "payment": payment, "customer_name": name, "delivery": delivery,
                       "finish": finish, "price_of": list(price_of), "not_sold": list(not_sold), "say": say})


def add(sku, qty):
    return {"op": "add", "sku": sku, "qty": qty}


def remove(sku, qty=None):
    return {"op": "remove", "sku": sku, **({"qty": qty} if qty is not None else {})}


# ---- reading the model's answer ------------------------------------------------------------------

def test_a_plain_json_answer_is_read():
    plan = order_turn.parse_plan(note([add("SUGAR-1KG", 2)], "Anything else?", payment="cash", finish=True))
    assert plan.ops == [add("SUGAR-1KG", 2)] and plan.payment == "cash" and plan.finish is True
    assert plan.say == "Anything else?"


@pytest.mark.parametrize("wrapper", ["```json\n{}\n```", "```\n{}\n```", "Here you go: {}", "{}\nHope that helps!"])
def test_fences_and_stray_text_around_the_json_are_tolerated(wrapper):
    inner = note([add("SUGAR-1KG", 1)], "ok")
    assert order_turn.parse_plan(wrapper.replace("{}", inner)).ops == [add("SUGAR-1KG", 1)]


@pytest.mark.parametrize("bad", ["", "no json here", "[1, 2]", '{"ops": ', "null", "{{{"])
def test_unusable_answers_give_none(bad):
    assert order_turn.parse_plan(bad) is None


def test_wrong_types_are_dropped_not_trusted():
    plan = order_turn.parse_plan(json.dumps({"ops": "add sugar", "payment": 5, "customer_name": ["x"],
                                             "delivery": {}, "finish": "yes", "say": 7}))
    assert plan.ops == [] and plan.payment is None and plan.customer_name is None
    assert plan.delivery is None and plan.finish is False and plan.say == ""


def test_only_a_real_true_means_finish():
    assert order_turn.parse_plan(note(finish=True)).finish is True
    assert order_turn.parse_plan('{"finish": "true"}').finish is False
    assert order_turn.parse_plan('{"finish": 1}').finish is False


def test_non_dict_operations_are_dropped():
    plan = order_turn.parse_plan(json.dumps({"ops": [add("SUGAR-1KG", 1), "x", 3, None]}))
    assert plan.ops == [add("SUGAR-1KG", 1)]


def test_price_of_wrong_types_is_dropped():
    assert order_turn.parse_plan('{"price_of": "GHEE-500"}').price_of == []
    assert order_turn.parse_plan('{"price_of": ["GHEE-500", 3, null]}').price_of == ["GHEE-500"]


def test_the_instructions_name_the_json_fields_and_use_the_shops_own_skus():
    text = order_turn.prompt_section([("SUGAR-1KG", "Sugar", "kg"), ("OIL-1L", "Sunflower oil", "litre")])
    for word in ("ops", "payment", "customer_name", "delivery", "finish", "price_of", "say", "SUGAR-1KG", "OIL-1L",
                 "OUT OF STOCK", "ONE JSON object", "dedh 1.5", "okati 1", "not_sold", "EVERY item"):
        assert word in text


def test_the_schema_lists_every_field_the_plan_reads():
    props = order_turn.SCHEMA["properties"]
    assert set(props) == {"ops", "payment", "customer_name", "delivery", "finish", "balance_query", "price_of", "not_sold", "say"}
    assert set(order_turn.SCHEMA["required"]) == set(props) and order_turn.SCHEMA["additionalProperties"] is False
    assert set(props["ops"]["items"]["properties"]) == {"op", "sku", "qty"}


# ---- building the reply: the code speaks -----------------------------------------------------------

def reply(session, raw, language="en-IN", closing=None):
    plan = order_turn.parse_plan(raw)
    result = session.apply(plan.ops, plan.payment, plan.customer_name, plan.delivery, plan.finish)
    return order_turn.compose(plan, result, session, language, closing=closing)


def test_an_added_item_is_confirmed_by_the_code_with_a_fixed_follow_up(session):
    assert reply(session, note([add("SUGAR-1KG", 2)], "whatever the model says")) == \
        "Added 2 kilo Sugar 88 rupees. Total so far 88 rupees. Anything else?"


def test_the_models_narration_and_its_own_totals_are_not_spoken(session):
    text = reply(session, note([add("SUGAR-1KG", 1), add("OIL-1L", 1)],
                               "[LINES] 4 packets added. Total so far 999 rupees. Delivery at 5 PM. Anything else?"))
    assert "999" not in text and "5 PM" not in text and "4 packets" not in text
    assert text == "Added 1 kilo Sugar 44 rupees, 1 litre Sunflower oil 165 rupees. Total so far 209 rupees. Anything else?"


def test_a_turn_where_the_model_said_nothing_and_nothing_changed_asks_what_comes_next(session):
    """The first phone call heard "Sorry, I did not catch that" three times after the caller said their own name."""
    assert reply(session, note([], "")) == "What would you like to order?"
    assert reply(session, note([], ""), "hi-IN") == "आपको क्या चाहिए?"
    assert reply(session, note([], ""), "te-IN") == "మీకు ఏమి కావాలి?"
    reply(session, note([add("SUGAR-1KG", 1)], "x"))
    assert reply(session, note([], "")) == "Anything else?"
    assert reply(session, note([], ""), "hi-IN") == "और कुछ चाहिए?"


def test_a_turn_where_the_model_did_speak_still_uses_its_words(session):
    assert reply(session, note([], "We are open until nine in the evening.")) == "We are open until nine in the evening."


def test_the_follow_up_question_is_in_the_callers_language(session):
    assert reply(session, note([add("SUGAR-1KG", 2)], "x"), "hi-IN") == \
        "2 किलो चीनी 88 रुपये जोड़ दिया। अभी तक कुल 88 रुपये। और कुछ चाहिए?"
    assert reply(session, note([add("RICE-1KG", 1)], "x"), "te-IN").endswith("ఇంకా ఏదైనా కావాలా?")


def test_that_is_all_reads_the_whole_order_and_asks_how_to_pay(session):
    session.apply([add("SUGAR-1KG", 2), add("OIL-1L", 1)])
    assert reply(session, note([], "model words", finish=True)) == \
        "Your order: 2 kilo Sugar 88 rupees, 1 litre Sunflower oil 165 rupees. Total 253 rupees. " \
        "How would you like to pay: cash, UPI or credit?"


def test_that_is_all_in_hindi_and_telugu_asks_in_that_language(session):
    session.apply([add("SUGAR-1KG", 2)])
    assert reply(session, note([], "x", finish=True), "hi-IN").endswith("पेमेंट कैसे करेंगे: कैश, यूपीआई या उधार?")
    assert reply(session, note([], "x", finish=True), "te-IN").endswith("చెల్లింపు ఎలా చేస్తారు: నగదు, యూపీఐ లేదా అప్పు?")


def test_that_is_all_does_not_ask_again_if_payment_is_already_chosen(session):
    session.apply([add("SUGAR-1KG", 1)], payment="cash")
    text = reply(session, note([], "x", finish=True))
    assert text == "Your order: 1 kilo Sugar 44 rupees. Total 44 rupees."


def test_that_is_all_with_nothing_ordered_does_not_ask_for_payment(session):
    assert reply(session, note([], "x", finish=True)) == "Nothing in your order yet."


def test_a_refusal_is_heard_with_the_read_back_when_the_caller_says_that_is_all(session):
    session.apply([add("SUGAR-1KG", 1)])
    text = reply(session, note([add("PANEER-200", 1)], "x", finish=True))
    assert text.startswith("Paneer is not available today. Your order: 1 kilo Sugar 44 rupees.")


def test_a_refusal_alone_gets_the_follow_up_question(session):
    assert reply(session, note([add("PANEER-200", 1)], "Paneer is out of stock, sorry!")) == \
        "Paneer is not available today. Anything else?"
    assert reply(session, note([add("NOPE-1", 1)], "x")) == "I could not find that item in our list. Anything else?"


def test_a_price_question_is_answered_from_the_stock_list_not_by_the_model(session):
    assert reply(session, note([], "The price of ghee is 120 rupees per litre.", price_of=["GHEE-500", "RICE-1KG"])) == \
        "Ghee is 330 rupees per packet. Rice (Sona Masoori) is 60 rupees per kilo. Anything else?"


def test_prices_in_hindi_and_telugu(session):
    assert reply(session, note([], "x", price_of=["SUGAR-1KG", "LEMON-1"]), "hi-IN") == \
        "चीनी 44 रुपये प्रति किलो है। नींबू 5 रुपये प्रति नग है। और कुछ चाहिए?"
    assert reply(session, note([], "x", price_of=["SUGAR-1KG"]), "te-IN") == \
        "చక్కెర కిలోకి 44 రూపాయలు. ఇంకా ఏదైనా కావాలా?"


def test_an_unknown_sku_in_price_of_changes_nothing(session):
    assert reply(session, note([], "We open at 8 AM.", price_of=["NOPE", "", "GHEE"])) == "We open at 8 AM."


# ---- nothing about the order happened: the model's own words ------------------------------------------

def test_a_question_about_the_shop_gets_the_models_answer(session):
    assert reply(session, note([], "We open at 8 AM.")) == "We open at 8 AM."


def test_the_model_can_ask_for_a_read_back_when_nothing_changed(session):
    session.apply([add("SUGAR-1KG", 2)])
    assert reply(session, note([], "[ORDER]")) == "Your order: 2 kilo Sugar 88 rupees. Total 88 rupees."


def test_stray_placeholders_never_reach_the_caller(session):
    text = reply(session, note([], "Hello [NAME], welcome [LINES]"))
    assert "[" not in text and "]" not in text and text == "Hello , welcome"


def test_the_model_writing_an_amount_itself_is_logged(session, caplog):
    with caplog.at_level(logging.WARNING, logger="order_turn"):
        reply(session, note([], "Sugar is 44 rupees."))
    assert any("amount itself" in r.message for r in caplog.records)


# ---- the closing sentence is the shop's, not the model's ----------------------------------------------------

def test_when_payment_is_chosen_the_shops_closing_replaces_the_models_words(session):
    session.apply([add("SUGAR-1KG", 1)])
    text = reply(session, note([], "Your delivery will be at 5:30 PM at 123 Main Street.", payment="cash"),
                 closing="CLOSING.")
    assert text == "CLOSING."


def test_a_change_made_on_the_same_turn_as_payment_is_still_said(session):
    text = reply(session, note([add("SUGAR-1KG", 1)], "ok", payment="upi"), closing="CLOSING.")
    assert text == "Added 1 kilo Sugar 44 rupees. Total so far 44 rupees. CLOSING."


def test_that_is_all_and_the_payment_on_one_turn_reads_the_order_then_closes(session):
    session.apply([add("SUGAR-1KG", 1)])
    text = reply(session, note([], "x", payment="cash", finish=True), closing="CLOSING.")
    assert text == "Your order: 1 kilo Sugar 44 rupees. Total 44 rupees. CLOSING."


def test_the_closing_is_not_used_when_payment_did_not_change(session):
    session.apply([], payment="cash")
    assert reply(session, note([], "We open at 8.", payment="cash"), closing="CLOSING.") == "We open at 8."
    assert reply(session, note([], "We open at 8."), closing="CLOSING.") == "We open at 8."


def test_without_a_closing_the_models_words_are_used(session):
    assert reply(session, note([], "Thanks!", payment="cash"), closing=None) == "Thanks!"


# ---- a whole conversation through the real shop --------------------------------------------------

class ScriptedModel:
    """Stands in for the language model: returns the next scripted JSON and records what it was asked."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, model, messages, max_tokens, temperature, schema=None):
        self.prompts.append({"system": messages[0]["content"], "messages": messages, "max_tokens": max_tokens,
                             "temperature": temperature, "schema": schema})
        return self.answers.pop(0)


@pytest.fixture
def manager():
    return cm.ConversationManager(SHOP, "test-model", 100, 0.5)


def talk(manager, session, transcript, language="hi-IN", history=None):
    sentences = [s for s, _ in manager.handle_turn_streaming(transcript, history or [], "", language, order=session)]
    return " ".join(sentences)


def test_the_manager_picks_the_closing_by_language_and_by_credit(manager):
    assert "45 minutes" in manager._closing_for("cash", "en-IN")
    assert "45 मिनट" in manager._closing_for("upi", "hi-IN")
    assert "45 నిమిషాలు" in manager._closing_for("cash", "te-IN")
    assert "confirm your credit" in manager._closing_for("udhaar", "en-IN")
    assert "उधार" in manager._closing_for("udhaar", "hi-IN")
    assert "45 minutes" in manager._closing_for("cash", "ta-IN")           # unknown language: English


def test_a_whole_call_ends_with_the_right_order_on_disk(manager, session, monkeypatch, tmp_path):
    model = ScriptedModel(
        note([add("SUGAR-1KG", 2), add("OIL-1L", 1)], "ok"),
        note([add("MAGGI-70", 1)], "ok"),
        note([], "ok", finish=True),
        note([], "ok", payment="cash", name="Ramesh", delivery="home"),
    )
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    said = [talk(manager, session, t) for t in ("do kilo चीनी aur ek litre sunflower oil", "ek packet Maggi bhi",
                                                  "bas itna hi", "cash, mera naam Ramesh hai")]
    assert said[0] == "2 किलो चीनी 88 रुपये, 1 लीटर सूरजमुखी तेल 165 रुपये जोड़ दिया। अभी तक कुल 253 रुपये। और कुछ चाहिए?"
    assert said[1] == "1 पैकेट मैगी नूडल्स 14 रुपये जोड़ दिया। अभी तक कुल 267 रुपये। और कुछ चाहिए?"
    assert "कुल 267 रुपये।" in said[2] and said[2].endswith("पेमेंट कैसे करेंगे: कैश, यूपीआई या उधार?")
    assert said[3] == manager._closing_for("cash", "hi-IN")                # the shop's own sentence, not the model's

    record = session.close(tmp_path)
    assert record["total"] == 267 and record["status"] == "confirmed" and record["customer"] == "Ramesh"
    assert [(i["sku"], i["qty"], i["line_total"]) for i in record["items"]] == [
        ("SUGAR-1KG", 2, 88), ("OIL-1L", 1, 165), ("MAGGI-70", 1, 14)]


def test_the_model_is_shown_the_order_so_far_but_never_an_amount_of_it(manager, session, monkeypatch):
    model = ScriptedModel(note([add("SUGAR-1KG", 2)], "x"), note([], "ok"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "do kilo chini")
    talk(manager, session, "kitna hua?")
    first, second = model.prompts
    assert "CURRENT ORDER: empty." in first["system"] and "ORDER MODE" in first["system"]
    assert "SUGAR-1KG Sugar 2 kg" in second["system"]
    state = second["system"].split("CURRENT ORDER:")[1].split("\n\n")[0]
    assert "88" not in state and "rupee" not in state
    assert first["max_tokens"] == manager.order_tokens >= 200       # the JSON note needs room
    assert "CATALOGUE" in first["system"] and "SUGAR-1KG | Sugar | चीनी | చక్కెర | kg" in first["system"]     # every item, every turn
    assert "PANEER-200 | Paneer | पनीर | పనీర్ | packet | OUT OF STOCK" in first["system"]


def test_every_order_turn_asks_for_the_strict_schema_and_a_low_temperature(manager, session, monkeypatch):
    model = ScriptedModel(note([], "hello"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "hello", "en-IN")
    assert model.prompts[0]["schema"] is order_turn.SCHEMA
    assert model.prompts[0]["temperature"] == manager.order_temperature <= 0.3


def test_an_unusable_model_answer_gives_the_fallback_and_changes_nothing(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel("sorry I cannot do that", "", "sorry again", ""))
    assert talk(manager, session, "do kilo chini", "hi-IN") == manager.fallback_messages["hi-in"]
    assert talk(manager, session, "do kilo chini", "te-IN") == manager.fallback_messages["te-in"]
    assert session.is_empty


def test_a_note_that_says_nothing_and_changes_nothing_asks_what_comes_next(manager, session, monkeypatch):
    # It used to be "Sorry, I did not catch that", which a caller heard three times after saying their own name.
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel(note([], "")))
    assert talk(manager, session, "hmm", "en-IN") == "What would you like to order?"


def test_a_note_that_cannot_be_read_at_all_still_gives_the_fallback(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel("not json at all", "still not json"))
    assert talk(manager, session, "hmm", "en-IN") == manager.fallback_messages["en-in"]


def test_the_model_cannot_add_an_item_the_shop_does_not_have_or_has_run_out_of(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel(note([add("DRAGONFRUIT-1KG", 1)], "x"),
                                                             note([add("PANEER-200", 1)], "x")))
    assert talk(manager, session, "dragon fruit", "en-IN") == "I could not find that item in our list. Anything else?"
    assert talk(manager, session, "paneer", "en-IN") == "Paneer is not available today. Anything else?"
    assert session.is_empty


def test_a_long_reply_is_spoken_as_separate_sentences(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel(note([add("SUGAR-1KG", 1)], "x")))
    sentences = [s for s, _ in manager.handle_turn_streaming("chini", [], "", "en-IN", order=session)]
    assert sentences == ["Added 1 kilo Sugar 44 rupees.", "Total so far 44 rupees.", "Anything else?"]


def test_plain_words_instead_of_json_get_one_more_try_with_a_reminder(manager, session, monkeypatch):
    model = ScriptedModel("Paneer aaj stock mein nahi hai.", note([add("PANEER-200", 1)], "x"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    text = talk(manager, session, "paneer bhi dena", "hi-IN")
    assert text == "पनीर आज उपलब्ध नहीं है। और कुछ चाहिए?"
    assert len(model.prompts) == 2
    retry = model.prompts[1]["messages"]
    assert retry[-2] == {"role": "assistant", "content": "Paneer aaj stock mein nahi hai."}
    assert "not the JSON object" in retry[-1]["content"]


def test_plain_words_twice_give_the_fallback_and_never_speak_the_plain_words(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel("I added the sugar for you.", "Done!"))
    assert talk(manager, session, "chini", "en-IN") == manager.fallback_messages["en-in"]
    assert session.is_empty


def test_an_empty_answer_is_not_retried(manager, session, monkeypatch):
    model = ScriptedModel("")
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    assert talk(manager, session, "chini", "en-IN") == manager.fallback_messages["en-in"]
    assert len(model.prompts) == 1                    # a failed request is not the same as a plain-text answer


def test_a_whole_payment_turn_through_the_manager_uses_the_closing(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel(
        note([add("SUGAR-1KG", 1)], "ok"),
        note([], "Delivery at 5 PM to your door!", payment="cash", name="Ramesh")))
    talk(manager, session, "chini", "en-IN")
    text = talk(manager, session, "cash, Ramesh", "en-IN")
    assert text == manager._closing_for("cash", "en-IN") and "5 PM" not in text
    assert session.payment == "cash" and session.customer == "Ramesh"


def test_without_an_order_the_old_streaming_path_is_used(manager, monkeypatch):
    monkeypatch.setattr(cm, "gemini_stream", lambda **kw: iter(["Namaste ji. ", "Kaise ", "madad karun?"]))
    monkeypatch.setattr(cm, "gemini_ask_json", lambda **kw: pytest.fail("the order path must not run"))
    sentences = [s for s, _ in manager.handle_turn_streaming("hello", [], "", "hi-IN")]
    assert " ".join(sentences) == "Namaste ji. Kaise madad karun?"


def _plain_shop(tmp_path):
    (tmp_path / "knowledge" / "core").mkdir(parents=True)
    (tmp_path / "config.yaml").write_text('system_prompt: "x"\nfallback_messages:\n  en-in: "sorry"\n', encoding="utf-8")


def test_a_shop_without_a_stock_list_ignores_the_order(tmp_path, monkeypatch):
    _plain_shop(tmp_path)
    plain = cm.ConversationManager(tmp_path, "m", 50, 0.1)
    assert plain.stock_items == []
    monkeypatch.setattr(cm, "gemini_stream", lambda **kw: iter(["Hello there."]))
    monkeypatch.setattr(cm, "gemini_ask_json", lambda **kw: pytest.fail("no order path without a stock list"))
    session = OrderSession("x", [], now=NOW)
    assert [s for s, _ in plain.handle_turn_streaming("hi", [], "", "en-IN", order=session)] == ["Hello there."]


def test_a_broken_stock_list_turns_order_taking_off_without_stopping_the_shop(tmp_path):
    _plain_shop(tmp_path)
    (tmp_path / "stock.json").write_text('{"items": [{"sku": "x"}]}', encoding="utf-8")
    assert cm.ConversationManager(tmp_path, "m", 50, 0.1).stock_items == []


def test_a_shop_without_closings_still_works(tmp_path):
    _plain_shop(tmp_path)
    assert cm.ConversationManager(tmp_path, "m", 50, 0.1)._closing_for("cash", "en-IN") is None


# ---- things the shop does not sell at all ---------------------------------------------------------------

def test_an_item_the_shop_does_not_sell_is_named_to_the_caller_and_the_rest_is_still_added(session):
    assert reply(session, note([add("PARLEG-100", 2)], "x", not_sold=["dragon fruit"])) ==         "Sorry, we do not have dragon fruit. Added 2 packets Parle-G biscuits 20 rupees. Total so far 20 rupees. Anything else?"


def test_not_sold_in_hindi_and_telugu(session):
    assert reply(session, note([], "x", not_sold=["आम"]), "hi-IN") == "माफ़ कीजिए, आम हमारे पास नहीं है। और कुछ चाहिए?"
    assert reply(session, note([], "x", not_sold=["మామిడి"]), "te-IN") == "క్షమించండి, మామిడి మా దగ్గర లేదు. ఇంకా ఏదైనా కావాలా?"


def test_several_unsold_items_are_listed_once_each_and_capped(session):
    text = reply(session, note([], "x", not_sold=["mango", "Mango", "kiwi", "plum", "pear", "fig"]))
    assert text.startswith("Sorry, we do not have mango, kiwi, plum, pear.") and "fig" not in text


def test_not_sold_names_are_cleaned_and_junk_is_ignored(session):
    assert reply(session, note([], "We open at 8.", not_sold=["", "   ", "!!!", 7])) == "We open at 8."
    assert "<" not in reply(session, note([], "x", not_sold=["<script>mango</script>"]))


def test_not_sold_is_said_along_with_the_read_back_at_the_end(session):
    session.apply([add("SUGAR-1KG", 1)])
    text = reply(session, note([], "x", finish=True, not_sold=["mango"]))
    assert text.startswith("Sorry, we do not have mango. Your order: 1 kilo Sugar 44 rupees.")


def test_not_sold_must_be_a_list_of_strings():
    assert order_turn.parse_plan('{"not_sold": "mango"}').not_sold == []
    assert order_turn.parse_plan('{"not_sold": ["mango", 3, null]}').not_sold == ["mango"]


def test_the_order_prompt_carries_the_whole_catalogue_and_no_product_sections(manager, session, monkeypatch):
    model = ScriptedModel(note([], "hello"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "aadha kilo pyaz aur ek kilo aloo chahiye")
    system = model.prompts[0]["system"]
    for sku in ("ONION-1KG", "POTATO-1KG", "ATTA-5KG", "TEA-250", "SOAP-100"):       # every item is there, whatever the words
        assert f"{sku} |" in system
    assert "SKU ONION-1KG" not in system                                 # the product sections of the search are left out
    assert "Relevant knowledge" not in system or "per kg" not in system.split("Relevant knowledge")[1]


# ---- the model repeats earlier changes (B-30, seen on the first valid run of gpt-oss-20b) -------------------------

def test_a_model_that_repeats_earlier_changes_on_later_turns_does_not_double_the_order(manager, session, monkeypatch, tmp_path):
    """The real failure of call h02: every later note carried the earlier adds again (Maggi 1->2, Parle-G 2->3, butter 1->2)."""
    model = ScriptedModel(
        note([add("MAGGI-70", 1), add("PARLEG-100", 2)], "ok"),
        note([add("BUTTER-100", 1), add("MAGGI-70", 1), add("PARLEG-100", 2)], "ok"),          # replays the first turn
        note([add("BUTTER-100", 1)], "ok", finish=True),                                       # replays the second turn
        note([add("BUTTER-100", 1)], "ok", payment="upi"),
    )
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    for words in ("Ek packet Maggi aur do packet Parle-G dena", "Aur ek Amul butter bhi", "bas itna hi", "UPI se dunga"):
        talk(manager, session, words, "hi-en")
    record = session.close(tmp_path)
    assert [(i["sku"], i["qty"]) for i in record["items"]] == [("MAGGI-70", 1), ("PARLEG-100", 2), ("BUTTER-100", 1)]
    assert record["total"] == 14 + 20 + 58 and record["payment"] == "upi"


def test_a_replayed_remove_is_ignored_but_a_real_one_is_not(manager, session, monkeypatch):
    model = ScriptedModel(
        note([add("RICE-1KG", 3), add("DAL-TOOR-1KG", 1)], "ok"),
        note([remove("RICE-1KG", 1)], "ok"),
        note([remove("RICE-1KG", 1)], "ok", payment="cash"),                                    # "Bas, cash": the last change again
    )
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "Teen kilo chawal aur ek kilo toor dal dena", "hi-en")
    talk(manager, session, "Chawal ek kilo kam kar do", "hi-en")
    talk(manager, session, "Bas, cash", "hi-en")
    assert float(session.lines["RICE-1KG"]) == 2 and float(session.lines["DAL-TOOR-1KG"]) == 1


def test_the_caller_naming_a_product_again_may_repeat_a_quantity(manager, session, monkeypatch):
    model = ScriptedModel(note([add("MAGGI-70", 2)], "ok"), note([add("MAGGI-70", 2)], "ok"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "do packet Maggi", "hi-en")
    talk(manager, session, "aur do packet Maggi", "hi-en")
    assert float(session.lines["MAGGI-70"]) == 4


def test_a_new_add_on_a_sentence_with_no_product_and_no_quantity_is_ignored(manager, session, monkeypatch):
    model = ScriptedModel(note([add("SUGAR-1KG", 2)], "ok"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "haan theek hai", "hi-en")
    assert session.lines == {}


def test_an_op_for_a_product_the_caller_named_is_always_kept(manager, session, monkeypatch):
    model = ScriptedModel(note([add("SUGAR-1KG", 1)], "ok"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, session, "ek packet sugar", "hi-en")
    assert float(session.lines["SUGAR-1KG"]) == 1


def test_has_quantity_sees_digits_and_number_words_in_three_languages():
    for text in ("2 kilo", "do kilo", "ek packet", "one litre", "రెండు కిలోలు", "दो किलो", "half kilo"):
        assert order_turn.has_quantity(text), text
    for text in ("UPI", "that is all", "bas itna hi", "cash, my name is Ramesh", "యూపీఐ", ""):
        assert not order_turn.has_quantity(text), text


# ---- "that is all" said at the end of a sentence, and thanks once the order is complete -----------------------------

@pytest.mark.parametrize("text", ["bas itna hi", "ek kilo tel, bas itna hi", "बस इतना ही, और कुछ नहीं।", "एक किलो तेल बस इतना ही।",
                                  "That's all.", "that is all!", "అంతే", "nothing else"])
def test_that_is_all_is_recognised_at_the_end_of_a_sentence(text):
    assert order_turn.says_that_is_all(text)


@pytest.mark.parametrize("text", ["", "do kilo cheeni", "bas do kilo", "no more than two kilo please", "that is all I need today and also oil",
                                  "bus ka time kya hai"])
def test_other_sentences_are_not_taken_as_that_is_all(text):
    assert not order_turn.says_that_is_all(text)


def test_a_that_is_all_the_model_missed_still_closes_the_list(manager, session, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", ScriptedModel(note([add("OIL-1L", 1)], "ok", finish=False)))
    text = talk(manager, session, "ek kilo tel, bas itna hi")
    assert "कुल 165 रुपये" in text and text.endswith("पेमेंट कैसे करेंगे: कैश, यूपीआई या उधार?")


def test_after_the_order_is_complete_a_thank_you_gets_thanks_not_a_second_read_back(session):
    reply(session, note([add("SUGAR-1KG", 1)], "x"))
    reply(session, note([], "", payment="cash", name="Ramesh", delivery="home"), closing="Thank you, your order is noted.")
    assert reply(session, note([], "")) == "Thank you! Your order is noted."                          # the model said nothing
    assert reply(session, note([], "", finish=True)) == "Thank you! Your order is noted."             # "that is all" again
    assert reply(session, note([], "", finish=True), "hi-IN") == "धन्यवाद! आपका ऑर्डर नोट हो गया है।"
    assert reply(session, note([], "You are welcome!")) == "You are welcome!"                          # the model's own words stand


def test_a_change_after_payment_is_still_confirmed(session):
    reply(session, note([add("SUGAR-1KG", 1)], "x"))
    reply(session, note([], "", payment="cash", delivery="home"), closing="Thank you, your order is noted.")
    assert "Added 1 packet" in reply(session, note([add("MAGGI-70", 1)], "x"))


@pytest.mark.parametrize("text", ["मुझे 2 किलो atta चाहिए और 1 लीटर तेल, बस इतना ही चाहिए।", "Bas itna hi chahiye", "bas itna hi hai ji",
                                  "That's all, thank you", "ఇంతే చాలు", "बस इतना ही, धन्यवाद"])
def test_that_is_all_followed_by_a_filler_word_still_counts(text):
    assert order_turn.says_that_is_all(text)
