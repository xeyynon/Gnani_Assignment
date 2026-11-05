"""
Tests for loan guidance on a call: how amounts are spoken, the session that asks for what is missing and works the
figures out, the keyword router, the turn through the conversation manager (the model replaced by scripted
answers), and the call's lifecycle in the main program. Every figure here comes from loan_calculator, which
reproduces the problem statement's example (project cost 10 lakh, EMI 15,438 for 78 months).

    python -m pytest tests/test_loan_flow.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import conversation_manager as cm  # noqa: E402
from dukaan_dost import loan_calculator, loan_turn, store  # noqa: E402
from dukaan_dost.loan_session import LoanSession, spoken_amount  # noqa: E402
from dukaan_dost.order_session import OrderSession  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"
NOW = datetime(2026, 11, 3, 11, 0, tzinfo=store.IST)


@pytest.fixture
def loan():
    return LoanSession("dukaan_dost", call_id="l1", now=NOW)


# ---- speaking amounts -------------------------------------------------------------------------------------

@pytest.mark.parametrize("amount, en, hi, te", [
    (5000, "5000 rupees", "5000 रुपये", "5000 రూపాయలు"),
    (90000, "90000 rupees", "90000 रुपये", "90000 రూపాయలు"),
    (100000, "1 lakh rupees", "1 लाख रुपये", "1 లక్ష రూపాయలు"),
    (135000, "1.35 lakh rupees", "1.35 लाख रुपये", "1.35 లక్షల రూపాయలు"),
    (150000, "1.5 lakh rupees", "1.5 लाख रुपये", "1.5 లక్షల రూపాయలు"),
    (112500, "1 lakh 12500 rupees", "1 लाख 12500 रुपये", "1 లక్ష 12500 రూపాయలు"),
    (4500000, "45 lakh rupees", "45 लाख रुपये", "45 లక్షల రూపాయలు"),
    (10000000, "1 crore rupees", "1 करोड़ रुपये", "1 కోటి రూపాయలు"),
    (15000000, "1.5 crore rupees", "1.5 करोड़ रुपये", "1.5 కోట్ల రూపాయలు"),
])
def test_amounts_from_a_lakh_up_are_spoken_in_lakh_words(amount, en, hi, te):
    """Plain six and seven digit numbers were read wrongly by Timbre in Hindi and Telugu (2026-11-03)."""
    assert spoken_amount(amount, "en-IN") == en
    assert spoken_amount(amount, "hi-IN") == hi
    assert spoken_amount(amount, "te-IN") == te


def test_no_spoken_amount_of_a_lakh_or_more_is_a_long_digit_run():
    import re
    for amount in (100000, 123456, 999999, 1000000, 4500000, 9999999, 12345678):
        for lang in ("en-IN", "hi-IN", "te-IN"):
            assert not re.search(r"\d{6,}", spoken_amount(amount, lang)), (amount, lang)


def test_a_language_key_or_code_both_work():
    assert spoken_amount(100000, "hi") == spoken_amount(100000, "hi-IN") == "1 लाख रुपये"
    assert spoken_amount(100000, None) == "1 lakh rupees"


# ---- the session ------------------------------------------------------------------------------------------------

def test_the_problem_statements_example_is_quoted_and_spoken(loan):
    result = loan.apply(100000, "margin_money", "kirana", "Nandyal", "en-IN")
    assert result.status == "quoted"
    q = loan.quote
    assert (q.project_cost, q.loan_amount, q.monthly_instalment, q.repayment_months) == (1000000, 900000, 15438, 78)
    text = loan.text(result)
    assert "I heard 1 lakh rupees as your own money, so a project of about 10 lakh rupees." in text
    assert "Term Loan Scheme" in text and "up to 9 lakh rupees at 8 percent a year" in text
    assert "6 months of grace" in text and "about 15438 rupees a month for 78 months" in text
    assert "approximate" in text


def test_a_project_cost_is_turned_into_the_callers_own_share(loan):
    result = loan.apply(1000000, "project_cost", language="en-IN")
    assert loan.quote.margin_money == 100000 and loan.quote.loan_amount == 900000
    assert "project cost of 10 lakh rupees, so you would put in 1 lakh rupees yourself" in loan.text(result)


def test_a_small_project_uses_the_micro_scheme(loan):
    result = loan.apply(10000, "margin_money", language="en-IN")
    assert loan.quote.scheme.key == "micro" and loan.quote.project_cost == 100000
    assert "Micro Finance Scheme" in loan.text(result) and "6.5 percent" in loan.text(result)


def test_when_a_cap_binds_the_callers_own_share_is_stated(loan):
    result = loan.apply(14000, "margin_money", language="en-IN")           # a 1.4 lakh project: 90 percent is 1.26 lakh, the cap 1.25
    assert loan.quote.loan_amount == 125000 and loan.quote.own_contribution == 15000 > loan.quote.margin_money
    assert "Your own share would be 15000 rupees, because the loan is capped." in loan.text(result)


def test_no_cap_sentence_when_the_caller_simply_puts_in_ten_percent(loan):
    result = loan.apply(100000, "margin_money", language="en-IN")
    assert "capped" not in loan.text(result)


def test_an_amount_with_no_kind_is_asked_about_then_answered(loan):
    r1 = loan.apply(50000, None, language="en-IN")
    assert r1.status == "ask_kind" and loan.quote is None
    assert loan.text(r1) == "I heard 50000 rupees. Is that your own money, or the whole project cost?"
    r2 = loan.apply(None, "margin_money", language="en-IN")                 # the answer: "my own money"
    assert r2.status == "quoted" and loan.quote.project_cost == 500000


def test_a_new_amount_replaces_the_old_quote(loan):
    loan.apply(100000, "margin_money")
    loan.apply(10000, "margin_money")
    assert loan.quote.project_cost == 100000 and loan.heard_amount == 10000


def test_nothing_said_yet_asks_for_the_amount(loan):
    r = loan.apply(None, None, "tea stall", "Kurnool", "en-IN")
    assert r.status == "ask_amount" and loan.business == "tea stall" and loan.place == "Kurnool"
    assert loan.text(r) == "How much money can you put in yourself, or what will the whole project cost?"


@pytest.mark.parametrize("bad", [0, -5, "abc", True, float("nan"), float("inf"), 10 ** 12])
def test_nonsense_amounts_are_refused_and_nothing_is_quoted(loan, bad):
    r = loan.apply(bad, "margin_money", language="en-IN")
    assert r.status == "bad_amount" and loan.quote is None
    assert "could not understand that amount" in loan.text(r)


def test_a_project_above_the_scheme_limit_is_not_quoted(loan):
    r = loan.apply(6000000, "project_cost", language="en-IN")
    assert r.status == "not_covered" and not loan.quote.covered
    text = loan.text(r)
    assert "60 lakh rupees is above the 50 lakh rupees" in text and "EMI" not in text and "a month" not in text


def test_commas_and_text_numbers_are_accepted_as_rupees(loan):
    assert loan.apply("1,00,000", "margin_money").status == "quoted" and loan.quote.margin_money == 100000


def test_business_and_place_are_cleaned_and_remembered(loan):
    loan.apply(None, None, "  <b>tea</b>  stall ", "Kurnool" * 20)
    assert "<" not in loan.business and ">" not in loan.business and "tea" in loan.business and "stall" in loan.business
    assert len(loan.place) <= 40
    loan.apply(None, None, None, None)
    assert loan.place is not None                                          # kept when a later turn says nothing


def test_the_figures_in_the_hindi_and_telugu_sentences_match_english(loan):
    loan.apply(100000, "margin_money")
    assert loan.quote.monthly_instalment == 15438
    hi = loan.text(loan.apply(100000, "margin_money"), "hi-IN")
    te = loan.text(loan.apply(100000, "margin_money"), "te-IN")
    for text, ten_lakh, rupee in ((hi, "10 लाख", "रुपये"), (te, "10 లక్షల", "రూపాయలు")):
        assert "15438" in text and "78" in text and ten_lakh in text and rupee in text


# ---- the record -----------------------------------------------------------------------------------------------------------

def test_the_record_has_what_the_dashboard_reads(loan, tmp_path, monkeypatch):
    monkeypatch.setenv("ORDER_SYNTHETIC", "1")
    loan.apply(100000, "margin_money", "kirana", "Nandyal", "te-IN")
    record = loan.close(tmp_path)
    saved = json.loads((tmp_path / "dukaan_dost" / "loan_l1.json").read_text(encoding="utf-8"))
    assert saved["type"] == "loan" and saved["business"] == "kirana" and saved["place"] == "Nandyal"
    assert saved["language"] == "te-IN" and saved["synthetic"] is True and saved["monthly_instalment"] == 15438
    assert saved["covered"] is True and saved["indicative"] is True and record["project_cost"] == 1000000
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["problems"] == [] and snap["loans"][0]["loan_amount"] == 900000


def test_no_quote_means_no_file(loan, tmp_path):
    loan.apply(None, None, "tea stall", None)
    assert loan.close(tmp_path) is None and not (tmp_path / "dukaan_dost").exists()


def test_closing_twice_writes_once(loan, tmp_path):
    loan.apply(10000, "margin_money")
    assert loan.close(tmp_path) is not None and loan.close(tmp_path) is None


# ---- the router -------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "I want a loan for a tea stall", "mujhe business loan chahiye", "मुझे लोन चाहिए", "दुकान खोलनी है, कर्ज़ चाहिए",
    "నాకు రుణం కావాలి", "లోన్ గురించి చెప్పండి", "what is the EMI",
    "udyami scheme ke baare mein", "కిస్తీ ఎంత", "I want to start a business", "karz chahiye",
    "mujhe dukaan kholni hai, mere paas ek lakh hai", "business start karna hai, 2 lakh invest kar sakta hoon",
    "कारोबार के लिए पचास हज़ार चाहिए",
])
def test_loan_words_in_any_of_the_languages_start_loan_mode(text):
    assert loan_turn.detect(text)


@pytest.mark.parametrize("text", [
    "do kilo cheeni aur ek litre oil chahiye", "2 किलो आटा", "రెండు కిలోల బియ్యం", "cash, mera naam Ramesh hai",
    "అప్పు మీద ఇవ్వండి", "Give me 0.5 kilo of onions", "bas itna hi", "udhaar pe dena", "Maggi aur Parle-G",
    "what is the price of ghee", "", None,
])
def test_shop_talk_does_not_start_loan_mode(text):
    assert not loan_turn.detect(text)


# ---- reading the model's note and building the reply ---------------------------------------------------------------------------

def note(amount=None, kind=None, business=None, place=None, say=""):
    return json.dumps({"amount": amount, "amount_kind": kind, "business": business, "place": place, "say": say})


def test_the_note_is_read_defensively():
    plan = loan_turn.parse_plan(note(100000, "margin_money", "kirana", "Nandyal"))
    assert (plan.amount, plan.kind, plan.business, plan.place) == (100000, "margin_money", "kirana", "Nandyal")
    bad = loan_turn.parse_plan(json.dumps({"amount": "lots", "amount_kind": "salary", "business": 5, "place": [], "say": 3}))
    assert (bad.amount, bad.kind, bad.business, bad.place, bad.say) == (None, None, None, None, "")
    assert loan_turn.parse_plan("```json\n" + note(5) + "\n```").amount == 5
    assert loan_turn.parse_plan("no json") is None and loan_turn.parse_plan("") is None
    assert loan_turn.parse_plan(json.dumps({"amount": True})).amount is None


def test_the_schema_matches_the_plan_fields():
    props = loan_turn.SCHEMA["properties"]
    assert set(props) == {"amount", "amount_kind", "business", "place", "say"} == set(loan_turn.SCHEMA["required"])
    prompt = loan_turn.prompt_section()
    for word in ("LOAN MODE", "ONE JSON object", "lakh", "margin_money", "project_cost", "NO digits"):
        assert word in prompt


def reply(loan, raw, language="en-IN"):
    plan = loan_turn.parse_plan(raw)
    result = loan.apply(plan.amount, plan.kind, plan.business, plan.place, language=language)
    return loan_turn.compose(plan, result, loan, language)


def test_the_models_words_with_a_number_are_never_spoken(loan, caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="loan_turn"):
        text = reply(loan, note(100000, "margin_money", say="The interest is 12 percent and the EMI is 9999."))
    assert "12 percent" not in text and "9999" not in text and "15438" in text
    assert any("number in its own words" in r.message for r in caplog.records)


def test_a_digit_free_answer_to_a_question_is_kept_before_the_code_asks(loan):
    text = reply(loan, note(None, None, say="A moratorium is a grace period before you start repaying."))
    assert text.startswith("A moratorium is a grace period before you start repaying. How much money")


def test_the_models_words_are_not_added_to_a_finished_quote(loan):
    text = reply(loan, note(10000, "margin_money", say="Great choice, good luck!"))
    assert "Great choice" not in text and "Micro Finance Scheme" in text


# ---- through the conversation manager -----------------------------------------------------------------------------------------

class Scripted:
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, model, messages, max_tokens, temperature, schema=None):
        self.prompts.append({"system": messages[0]["content"], "schema": schema, "max_tokens": max_tokens})
        return self.answers.pop(0)


@pytest.fixture
def manager():
    return cm.ConversationManager(SHOP, "test-model", 100, 0.5)


def talk(manager, transcript, language, loan, order=None):
    return " ".join(s for s, _ in manager.handle_turn_streaming(transcript, [], "", language, order=order, loan=loan))


def test_a_loan_call_in_hindi_end_to_end(manager, loan, monkeypatch, tmp_path):
    model = Scripted(note(None, None, "kirana", "Nandyal"), note(100000, "margin_money"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    first = talk(manager, "मुझे दुकान के लिए लोन चाहिए", "hi-IN", loan)
    assert first == "आप अपनी तरफ़ से कितना पैसा लगा सकते हैं, या पूरे प्रोजेक्ट की लागत कितनी होगी?" and loan.active
    second = talk(manager, "मेरे पास एक लाख रुपये हैं", "hi-IN", loan)        # no loan word: the mode is sticky
    assert "1 लाख रुपये आपका अपना पैसा सुना, यानी लगभग 10 लाख रुपये का प्रोजेक्ट" in second
    assert "15438 रुपये महीने की किस्त, 78 महीने तक" in second and "अंदाज़न" in second
    assert model.prompts[0]["schema"] is loan_turn.SCHEMA and "LOAN MODE" in model.prompts[0]["system"]
    record = loan.close(tmp_path)
    assert record["business"] == "kirana" and record["place"] == "Nandyal" and record["monthly_instalment"] == 15438


def test_a_telugu_and_an_english_loan_turn(manager, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", Scripted(note(10000, "margin_money"), note(2500000, "project_cost")))
    te = talk(manager, "నాకు లోన్ కావాలి", "te-IN", LoanSession("dukaan_dost", now=NOW))
    assert "10000 రూపాయలు మీ సొంత డబ్బుగా విన్నాను" in te and "1 లక్ష రూపాయలు ప్రాజెక్ట్" in te
    en = talk(manager, "I want a loan, my project costs twenty five lakh", "en-IN", LoanSession("dukaan_dost", now=NOW))
    assert "project cost of 25 lakh rupees" in en and "Term Loan Scheme" in en


def test_the_loan_prompt_is_short_and_has_no_catalogue(manager, loan, monkeypatch):
    model = Scripted(note(None))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    talk(manager, "loan chahiye", "hi-IN", loan)
    system = model.prompts[0]["system"]
    assert "CATALOGUE" not in system and "ORDER MODE" not in system and len(system) < 4500


def test_shop_talk_still_goes_to_the_order_flow_even_with_a_loan_session_present(manager, loan, monkeypatch):
    order = OrderSession("dukaan_dost", manager.stock_items, now=NOW)
    model = Scripted(json.dumps({"ops": [{"op": "add", "sku": "SUGAR-1KG", "qty": 2}], "payment": None,
                                 "customer_name": None, "delivery": None, "finish": False, "price_of": [],
                                 "not_sold": [], "say": ""}))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    text = talk(manager, "do kilo cheeni", "hi-IN", loan, order)
    assert "2 किलो चीनी 44" not in text and "88 रुपये" in text and not loan.active


def test_an_unusable_loan_answer_gives_the_fallback_and_quotes_nothing(manager, loan, monkeypatch):
    monkeypatch.setattr(cm, "gemini_ask_json", Scripted("I cannot do that", "still no"))
    assert talk(manager, "loan chahiye", "hi-IN", loan) == manager.fallback_messages["hi-in"] and loan.quote is None


def test_plain_words_get_one_retry_in_loan_mode_too(manager, loan, monkeypatch):
    model = Scripted("Sure, how much?", note(10000, "margin_money"))
    monkeypatch.setattr(cm, "gemini_ask_json", model)
    assert "Micro Finance Scheme" in talk(manager, "I need a loan", "en-IN", loan) and len(model.prompts) == 2


# ---- the call's lifecycle in the main program ---------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


@pytest.fixture
def clean_app(app, monkeypatch, tmp_path):
    monkeypatch.setattr(store, "ORDERS_DIR", tmp_path)
    app._finish_order("setup")
    yield app
    app._finish_order("teardown")


def test_every_call_starts_with_an_inactive_loan_session(clean_app):
    clean_app._set_active_shop()
    assert clean_app._loan is not None and not clean_app._loan.active and clean_app._loan.quote is None


def test_a_loan_quote_is_saved_when_the_call_ends(clean_app, tmp_path):
    clean_app._set_active_shop()
    clean_app._loan.apply(100000, "margin_money", "kirana", "Nandyal", "hi-IN")
    clean_app._clear_history("call ended")
    files = list((tmp_path / "dukaan_dost").glob("loan_*.json"))
    assert len(files) == 1 and json.loads(files[0].read_text(encoding="utf-8"))["monthly_instalment"] == 15438
    assert clean_app._loan is None


def test_a_call_with_no_quote_leaves_no_loan_file_and_the_next_call_starts_fresh(clean_app, tmp_path):
    clean_app._set_active_shop()
    first = clean_app._loan
    first.apply(None, None, "tea stall", None)
    clean_app._clear_history("call ended")
    clean_app._set_active_shop()
    assert clean_app._loan is not first and not list((tmp_path).glob("dukaan_dost/loan_*.json"))


def test_the_resets_after_a_new_call_do_not_discard_its_loan_session(clean_app):
    clean_app._set_active_shop()
    opened = clean_app._loan
    clean_app._clear_history("new node replay-x")
    assert clean_app._loan is opened


def test_the_reply_path_hands_the_loan_session_to_the_manager(clean_app, monkeypatch):
    seen = {}

    class Fake:
        stock_items = []

        def handle_turn_streaming(self, transcript, recent, context, language_code, order=None, loan=None):
            seen["loan"] = loan
            yield "ok.", language_code

    monkeypatch.setattr(clean_app, "_get_conv_mgr", lambda shop=None: Fake())
    clean_app._loan = LoanSession("dukaan_dost", now=NOW)
    list(clean_app._ask_streaming("hello", "en-IN"))
    assert seen["loan"] is clean_app._loan


def test_the_calculator_still_reproduces_the_problem_statement():
    q = loan_calculator.quote(100000)
    assert (q.project_cost, q.loan_amount, q.monthly_instalment, q.repayment_months) == (1000000, 900000, 15438, 78)


# ---- the loan event for the call page ----------------------------------------------------------

def test_a_new_quote_is_sent_to_the_call_page_with_the_calculators_figures():
    seen = []
    s = LoanSession("dukaan_dost", call_id="e1", now=NOW, listener=seen.append)
    s.apply(amount=500000, kind="project_cost", business="tailor", place="Guntur")
    assert len(seen) == 1 and seen[0]["type"] == "loan"
    assert seen[0]["project_cost"] == 500000 and seen[0]["margin_money"] == 50000
    assert seen[0]["business"] == "tailor" and seen[0]["indicative"] is True
    s.apply(amount=100000, kind="margin_money")
    assert len(seen) == 2 and seen[1]["project_cost"] == 1000000


def test_nothing_is_sent_while_the_agent_is_still_asking_and_a_broken_listener_changes_nothing():
    seen = []
    s = LoanSession("dukaan_dost", call_id="e2", now=NOW, listener=seen.append)
    s.apply(amount=100000)                       # amount heard, kind unknown: no quote yet
    s.apply()
    assert seen == []

    def boom(event):
        raise RuntimeError("page gone")
    t = LoanSession("dukaan_dost", call_id="e3", now=NOW, listener=boom)
    assert t.apply(amount=100000, kind="margin_money").status == "quoted"


@pytest.mark.parametrize("text", [
    "Do you charge interest on udhaar?", "Is the shop open for business on Sunday?", "what is the business hours",
    "उधार पर ब्याज लगेगा क्या", "मेरी योजना है कि कल सुबह आऊँ", "मेरा व्यापार है, 20 किलो चावल चाहिए", "I will invest in 10 kg rice",
    "मुझे लोन नहीं, दो किलो चीनी चाहिए", "no loan, two kilo sugar", "what's the subsidy price of sugar", "రేపటికి వాయిదా వేయండి",
    "ब्याज कितना लगेगा", "byaj kitna hai",
])
def test_ordinary_shop_talk_does_not_start_the_sticky_loan_mode(text):
    """Bug hunt 2026-11-05: words like business, interest and ब्याज alone moved the whole call into loan mode."""
    assert not loan_turn.detect(text)


@pytest.mark.parametrize("text", ["business ke liye 5 lakh ka byaj kitna hoga", "interest on a 2 lakh loan", "వ్యాపారం కోసం రెండు లక్షలు కావాలి"])
def test_a_weak_loan_word_beside_an_amount_scale_does_start_loan_mode(text):
    assert loan_turn.detect(text)


# ---- bug hunt of 2026-11-05: tiny amounts, a turn after hang-up -------------------------------------------------

@pytest.mark.parametrize("amount", [0.4, 0.49, 1e-9, 1, 9, 999])
def test_an_amount_under_a_thousand_rupees_is_a_mishearing_not_a_crash(loan, amount):
    r = loan.apply(amount, "margin_money")
    assert r.status == "bad_amount" and loan.quote is None
    assert "0 rupees" not in loan.text(loan.apply(amount), "en-IN")


def test_a_thousand_rupees_is_the_least_that_is_quoted(loan):
    assert loan.apply(1000, "margin_money").status == "quoted" and loan.quote.project_cost == 10000


def test_a_loan_turn_after_hang_up_quotes_shows_and_saves_nothing(tmp_path):
    seen = []
    s = LoanSession("dukaan_dost", call_id="z1", now=NOW, listener=seen.append)
    s.apply(100000, "margin_money")
    s.close(tmp_path)
    seen.clear()
    late = s.apply(500000, "project_cost", business="tea stall", place="Kurnool")
    assert late.status == "closed" and seen == [] and s.text(late, "en-IN") == ""
    assert s.quote.margin_money == 100000                      # the quote is still the one that was saved
