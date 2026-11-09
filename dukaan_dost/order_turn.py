"""
order_turn.py

One turn of an order call, between the language model and order_session.py:

  1. prompt_section(): the instructions that make the model answer with one small JSON object
     (which items, how many, payment, "that is all", and a short reply) instead of free text.
  2. parse_plan(): reads that object, tolerating code fences and stray text, and checks its types.
  3. compose(): builds the spoken reply. The model's own words carry placeholders, [LINES] and
     [ORDER]; the code fills them with the exact sentences about the order (order_session.py), so
     every amount a caller hears was computed by code, never by the model.

If the model leaves a placeholder out, the code still says what changed (and reads the order back
when the caller said that is all): the caller must always hear what happened to their order.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from .order_session import SAY, lang_key

log = logging.getLogger("order_turn")

_PLACEHOLDER = re.compile(r"\[[A-Z_]+\]")

# "That is all" said at the end of a sentence. The model sometimes ignores it when the same sentence also adds an item
# ("ek kilo tel, bas itna hi": heard on the third real phone call, 2026-11-09), so the code backs it up. Only the end of
# the sentence counts, and only these phrases: "bas" alone could be a bus, "no more" could be "no more than 2 kilo".
_THAT_IS_ALL = re.compile(
    r"(?:that'?s all|that is all|that'?s it|that is it|nothing else|bas itna(?: hi)?|itna hi|aur kuch nahi|और कुछ नहीं|"
    r"बस इतना(?: ही)?|इतना ही|ఇంతే|అంతే|ఇంకేమీ వద్దు)"
    r"(?:[\s,]+(?:चाहिए|चाहिये|है|हैं|जी|धन्यवाद|chahiye|hai|ji|please|thanks|thank you|చాలు|కావాలి))*$", re.IGNORECASE)


# At the payment step a one-word answer that the phone line garbled ("Gash", "Dash" for "cash", heard on the sixth test call,
# 2026-11-09) used to get "Sorry, we do not have Gash". These are the Latin-letter answers that are accepted when they are
# within one letter of the real word, and only while the payment is owed.
_PAYMENT_WORDS = {"cash": "cash", "upi": "upi", "udhaar": "udhaar", "udhar": "udhaar", "credit": "udhaar"}


def _one_letter_apart(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def payment_guess(transcript: str):
    """cash, upi or udhaar when the transcript is ONE Latin-letter word within a letter of that payment word, else None."""
    words = re.findall(r"[a-z]+", (transcript or "").lower())
    if len(words) != 1 or re.search(r"[^ -~]", transcript or ""):
        return None
    word = words[0]
    if len(word) < 3:
        return None
    for known, payment in _PAYMENT_WORDS.items():
        if _one_letter_apart(word, known):
            return payment
    return None


def says_that_is_all(transcript: str) -> bool:
    tail = re.sub(r"[\s.,!?।]+$", "", transcript or "")
    return bool(_THAT_IS_ALL.search(tail))
_AMOUNT = re.compile(r"(?:₹\s*\d|\d[\d,.]*\s*(?:rupees?|rs\b|रुपये|रुपए|రూపాయలు|రూపాయి))", re.IGNORECASE)


# The shape the model must answer in. Sent as a strict JSON schema where the service supports it
# (Groq does for qwen/qwen3.8-27b, checked 2026-11-02), which makes a plain-text answer impossible.
SCHEMA = {
    "type": "object",
    "properties": {
        "ops": {"type": "array", "items": {"type": "object", "properties": {
            "op": {"type": "string", "enum": ["add", "set", "remove"]},
            "sku": {"type": "string"},
            "qty": {"type": ["number", "null"]}},
            "required": ["op", "sku", "qty"], "additionalProperties": False}},
        "payment": {"type": ["string", "null"], "enum": ["cash", "upi", "udhaar", None]},
        "customer_name": {"type": ["string", "null"]},
        "delivery": {"type": ["string", "null"], "enum": ["home", "pickup", None]},
        "finish": {"type": "boolean"},
        "balance_query": {"type": "boolean"},
        "price_of": {"type": "array", "items": {"type": "string"}},
        "not_sold": {"type": "array", "items": {"type": "string"}},
        "say": {"type": "string"}},
    "required": ["ops", "payment", "customer_name", "delivery", "finish", "balance_query", "price_of", "not_sold", "say"],
    "additionalProperties": False,
}


@dataclass
class Plan:
    ops: list = field(default_factory=list)
    payment: str | None = None
    customer_name: str | None = None
    delivery: str | None = None
    finish: bool = False
    balance_query: bool = False
    price_of: list = field(default_factory=list)
    not_sold: list = field(default_factory=list)
    say: str = ""


def prompt_section(examples: list | None = None) -> str:
    """The order-mode instructions. `examples` is [(sku, english name, unit), ...]; the first two are used."""
    a = examples[0] if examples else ("ITEM-A", "item A", "kg")
    b = examples[1] if examples and len(examples) > 1 else ("ITEM-B", "item B", "packet")
    return f"""ORDER MODE. Your whole answer, to every message, is ONE JSON object and nothing else (even for a question, a greeting or an item we do not sell). The system does all money and speaks all prices, totals and order confirmations: never write one.
Fields: ops, payment, customer_name, delivery, finish, balance_query, price_of, not_sold, say.
- ops: changes made by the caller's LAST message only, never items already in CURRENT ORDER or mentioned earlier. {{"op": "add"|"set"|"remove", "sku": <a SKU from the CATALOGUE>, "qty": number}}. add = more of it, set = make the quantity exactly this, remove = take it out (qty = only part). One op for EVERY item named, even if another item in the message is not sold. If the last message is only about payment, a name, delivery or "that is all", ops is []. If an item or quantity is unclear: no op, ask in say.
- qty is in the item's own unit: kg and litre in steps of 0.25 (500 gram = 0.5), other units whole numbers. Number words: ek/okati 1, do/rendu 2 ("do" is two), teen/moodu 3, char/naalugu 4, paanch/aidu 5, chhe/aaru 6, saat/edu 7, aath/enimidi 8, nau/tommidi 9, das/padi 10, aadha/ara 0.5, dedh 1.5, dhai 2.5.
- Match what the caller says to the CATALOGUE in any of its names or spellings (Hindi and Telugu words, plurals, small mis-hearings such as chini/cheeni/छीनी = sugar). An item marked OUT OF STOCK still gets its add op (the system tells the caller). Only an item that is truly not in the CATALOGUE: no op, put its name in not_sold (the caller's words).
- price_of: SKUs whose price the caller asked for. finish: true only when the caller wants nothing more. payment: cash, upi or udhaar, only once chosen. customer_name: the caller's name whenever they say it, also when it is the whole message (the system asks for it when they want credit). delivery (home or pickup): only if said. balance_query: true when the caller asks how much they owe on credit (udhaar balance); the system answers from the credit book.
- say: a short reply in the caller's language, only for what the system does not cover (a greeting, a question about the shop from the knowledge, a question back). Delivery and shop facts: repeat the knowledge; if it is not there, say the shopkeeper will tell them. Digits for numbers. Otherwise "".
Examples (caller, then JSON):
"2 kilo {a[1]} and 1 {b[1]}" -> {{"ops": [{{"op": "add", "sku": "{a[0]}", "qty": 2}}, {{"op": "add", "sku": "{b[0]}", "qty": 1}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "balance_query": false, "price_of": [], "not_sold": [], "say": ""}}
"that's all" -> {{"ops": [], "payment": null, "customer_name": null, "delivery": null, "finish": true, "balance_query": false, "price_of": [], "not_sold": [], "say": ""}}
"cash, my name is Ramesh" -> {{"ops": [], "payment": "cash", "customer_name": "Ramesh", "delivery": null, "finish": false, "balance_query": false, "price_of": [], "not_sold": [], "say": ""}}
"make the {a[1]} 1 kilo, and what does the {b[1]} cost?" -> {{"ops": [{{"op": "set", "sku": "{a[0]}", "qty": 1}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "balance_query": false, "price_of": ["{b[0]}"], "not_sold": [], "say": ""}}
"how much do I owe? I am Ramesh" -> {{"ops": [], "payment": null, "customer_name": "Ramesh", "delivery": null, "finish": false, "balance_query": true, "price_of": [], "not_sold": [], "say": ""}}
"1 kilo of dragon fruit and 2 {b[1]}" -> {{"ops": [{{"op": "add", "sku": "{b[0]}", "qty": 2}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "balance_query": false, "price_of": [], "not_sold": ["dragon fruit"], "say": ""}}"""


def extract_json(text: str):
    """The first JSON object in the model's output, or None."""
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except ValueError:
            return None
    return None


# Number words in the three languages, for has_quantity(). "do" is also the Hinglish "give" (dena, de do), so it counts
# as a number here: the cost of being wrong is only that a guard stays off.
_QUANTITY_WORDS = ("one two three four five six seven eight nine ten half quarter dozen "
                   "ek do teen char chaar paanch panch chhe saat aath nau das aadha adha dedh dhai sawa "
                   "oka rendu moodu nalugu aidu ara "
                   "एक दो तीन चार पांच पाँच छह सात आठ नौ दस आधा डेढ़ ఒక రెండు మూడు నాలుగు ఐదు అర").split()
_QUANTITY_RE = re.compile(r"\d|(?<!\w)(?:" + "|".join(map(re.escape, _QUANTITY_WORDS)) + r")(?!\w)", re.IGNORECASE)


def has_quantity(text: str) -> bool:
    """Does the caller's sentence contain a digit or a number word? "UPI", "that is all" and "my name is Ramesh" do not."""
    return bool(text) and _QUANTITY_RE.search(text) is not None


def parse_plan(text: str) -> Plan | None:
    obj = extract_json(text)
    if obj is None:
        return None
    ops = obj.get("ops")
    return Plan(
        ops=[o for o in ops if isinstance(o, dict)] if isinstance(ops, list) else [],
        payment=obj.get("payment") if isinstance(obj.get("payment"), str) else None,
        customer_name=obj.get("customer_name") if isinstance(obj.get("customer_name"), str) else None,
        delivery=obj.get("delivery") if isinstance(obj.get("delivery"), str) else None,
        finish=obj.get("finish") is True,
        balance_query=obj.get("balance_query") is True,
        price_of=[s for s in obj["price_of"] if isinstance(s, str)] if isinstance(obj.get("price_of"), list) else [],
        not_sold=[s for s in obj["not_sold"] if isinstance(s, str)] if isinstance(obj.get("not_sold"), list) else [],
        say=obj.get("say") if isinstance(obj.get("say"), str) else "",
    )


def compose(plan: Plan, result, session, language, closing: str | None = None) -> str:
    """
    The reply to speak. When the turn touched the order (items added, changed, removed or refused; the
    caller said that is all; a price was asked; payment was chosen) the code says all of it, with a fixed
    follow-up question in the caller's language, and the model's own words are NOT used. On the real model
    those words narrated the change a second time with totals of its own that disagreed with the code's
    (209 and 221 beside the real 265), invented delivery times and addresses, and drifted into English
    during Hindi calls. The model's words are used only when nothing about the order happened: a greeting,
    a question about the shop.

    `closing` is the shop's own fixed sentence for the turn on which payment is chosen.
    """
    say = plan.say.strip()
    if _AMOUNT.search(say):
        log.warning(f"[ORDER] the model wrote an amount itself, against its instructions: {say!r}")
    lang = lang_key(language)
    prices = session.prices_text(plan.price_of, language)
    not_sold = session.not_sold_text(plan.not_sold, language)
    credit = session.credit_text(result, language)
    kinds = {e["kind"] for e in result.credit_events}
    blocked = bool(kinds & {"need_name", "over_limit"})          # the caller has to answer or choose again first
    # the order is complete on this turn: payment chosen (cash or UPI), credit approved or left to the shopkeeper,
    # or credit chosen at a shop that keeps no credit book
    completes = (not blocked) and (not session.is_empty) and bool(
        (kinds & {"approved", "unknown"})
        or (result.payment_set and (session.payment in ("cash", "upi") or (session.payment == "udhaar" and session.credit is None))))
    parts = []

    # The order is complete (payment chosen) and this turn changed nothing: a "thank you", or "that is all" said again.
    # Reading the whole order back again, or asking "Anything else?", was heard on the third real phone call.
    if result.changes:
        session.read_back_done = False                            # the order changed: a read-back is due again
    already_read_back = getattr(session, "read_back_done", False)
    was_closed = getattr(session, "order_closed", False)          # the order was already read back or closed earlier
    complete_and_quiet = was_closed and (not session.is_empty) and session.payment is not None and not blocked and not (
        result.changes or prices or not_sold or credit or result.payment_set or plan.balance_query)
    if complete_and_quiet and (plan.finish or not say) and "[ORDER]" not in say:
        return SAY[lang]["thanks"]

    if plan.finish:
        parts += [session.rejections_text(result.changes, language), not_sold]
        if not already_read_back:                                 # the whole order is read back once, not at every turn
            parts.append(session.readback(language))
            session.read_back_done = True
    elif result.changes or prices or not_sold or credit:
        parts += [not_sold, session.changes_text(result.changes, language), prices]
    elif not (closing and completes):
        # nothing about the order happened: the model's own words, with a read-back where it asked for one
        text = say.replace("[ORDER]", session.readback(language)).replace("[LINES]", "")
        text = " ".join(_PLACEHOLDER.sub("", text).split())
        if not text:
            # The model said nothing and changed nothing (a name, a "hello", a word it did not follow). That used
            # to fall through to "Sorry, I did not catch that", which a caller heard three times in a row on the
            # first phone call (2026-11-07) after saying their own name. Say what comes next instead.
            if session.is_empty:
                return SAY[lang]["what"]
            if session.payment is not None:
                return SAY[lang]["thanks"]
            return SAY[lang]["pay" if session.finished else "more"]     # waiting for the payment: ask for it again
        return text

    parts.append(credit)
    if (plan.finish and session.payment is not None and not blocked) or (closing and completes):
        session.order_closed = True                               # from now on a thank-you gets thanks, not a second read-back
    if closing and completes:
        parts.append(closing)
    elif blocked:
        pass                                                     # the credit sentence already asks the next question
    elif plan.finish and not session.is_empty and session.payment is None:
        parts.append(SAY[lang]["pay"])
    elif not plan.finish:
        parts.append(SAY[lang]["more"])
    return " ".join(" ".join(p for p in parts if p).split())
