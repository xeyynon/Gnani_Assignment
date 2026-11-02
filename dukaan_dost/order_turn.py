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
        "price_of": {"type": "array", "items": {"type": "string"}},
        "not_sold": {"type": "array", "items": {"type": "string"}},
        "say": {"type": "string"}},
    "required": ["ops", "payment", "customer_name", "delivery", "finish", "price_of", "not_sold", "say"],
    "additionalProperties": False,
}


@dataclass
class Plan:
    ops: list = field(default_factory=list)
    payment: str | None = None
    customer_name: str | None = None
    delivery: str | None = None
    finish: bool = False
    price_of: list = field(default_factory=list)
    not_sold: list = field(default_factory=list)
    say: str = ""


def prompt_section(examples: list | None = None) -> str:
    """The order-mode instructions. `examples` is [(sku, english name, unit), ...]; the first two are used."""
    a = examples[0] if examples else ("ITEM-A", "item A", "kg")
    b = examples[1] if examples and len(examples) > 1 else ("ITEM-B", "item B", "packet")
    return f"""ORDER MODE. You do not add up money and you do not say the prices or totals of the order: the system does that and speaks them. Your whole answer, for every message the caller sends, is ONE JSON object and nothing else, even for a question, a greeting, or an item we do not have:
{{"ops": [{{"op": "add", "sku": "{a[0]}", "qty": 2}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "price_of": [], "not_sold": [], "say": "short spoken reply"}}
- ops: the changes to the order made by what the caller just said. op is add (more of an item), set (make the quantity exactly this) or remove (take the item out; give qty to take out only part). sku must be one of the SKUs shown in the product knowledge below. qty is in that item's own unit: kg and litre may be 0.25, 0.5, 0.75, 1, 1.5 and so on (500 gram is 0.5 kg); every other unit is a whole number. Number words: ek/okati 1, do/rendu 2, teen/moodu 3, char/naalugu 4, paanch/aidu 5, chhe/aaru 6, saat/edu 7, aath/enimidi 8, nau/tommidi 9, das/padi 10, aadha/ara 0.5, dedh 1.5, dhai 2.5. \"do\" is the number two, not the English word. If the item or the quantity is unclear, make no op and ask one short question in say.
- Give one op for EVERY item the caller names in a message, even when another item in the same message is one we cannot sell: never drop an item because of another.
- An item marked OUT OF STOCK still gets its add op (answer in JSON like any other message): the system tells the caller it is not available. An item that is not in the knowledge at all: no op, say so in say.
- finish: true only when the caller says they want nothing more. The system then reads the whole order and the total aloud, so do not repeat it; ask how they will pay.
- payment: cash, upi or udhaar, only once the caller has chosen. customer_name: only if the caller said their name. delivery: home or pickup, only if they said.
- say: the spoken reply in the caller's language, one to three short sentences. Write [LINES] where the system should say what was just added or changed, with the running total, and [ORDER] where it should read the whole order with the total. Never write the price or total of the order yourself. Delivery charges, times and payment details: repeat the knowledge below, and if it is not there say the shopkeeper will tell them. Digits for numbers, never number words.
- not_sold: the names, in the caller's words, of things they asked for that are not in the product knowledge at all (give no op for them). The system tells the caller.
- price_of: the SKUs of items whose price the caller asked for. The system says the price from the stock list. Never write any price yourself, not even from the knowledge below, and never say that an item is out of stock or added or removed: the system says all of that.
- If the order did not change (a question, a greeting, a payment choice), use "ops": [] and answer in say.
Examples (the caller's words, then your JSON):
Caller: "2 kilo {a[1]} and 1 {b[1]} please"
{{"ops": [{{"op": "add", "sku": "{a[0]}", "qty": 2}}, {{"op": "add", "sku": "{b[0]}", "qty": 1}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "price_of": [], "not_sold": [], "say": "[LINES] Anything else?"}}
Caller: "that's all"
{{"ops": [], "payment": null, "customer_name": null, "delivery": null, "finish": true, "price_of": [], "not_sold": [], "say": "[ORDER] How would you like to pay: cash, UPI or credit?"}}
Caller: "cash"
{{"ops": [], "payment": "cash", "customer_name": null, "delivery": null, "finish": false, "price_of": [], "not_sold": [], "say": "Thank you, your order is noted."}}
Caller: "what does the {b[1]} cost?"
{{"ops": [], "payment": null, "customer_name": null, "delivery": null, "finish": false, "price_of": ["{b[0]}"], "not_sold": [], "say": "Anything else?"}}
Caller: "make the {a[1]} 1 kilo"
{{"ops": [{{"op": "set", "sku": "{a[0]}", "qty": 1}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "price_of": [], "not_sold": [], "say": "[LINES] Anything else?"}}
Caller: "take out the {b[1]}"
{{"ops": [{{"op": "remove", "sku": "{b[0]}"}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "price_of": [], "not_sold": [], "say": "[LINES] Anything else?"}}
Caller: "1 kilo of dragon fruit and 2 {b[1]}"
{{"ops": [{{"op": "add", "sku": "{b[0]}", "qty": 2}}], "payment": null, "customer_name": null, "delivery": null, "finish": false, "price_of": [], "not_sold": ["dragon fruit"], "say": ""}}
Remember: every answer is the JSON object, even when the only thing to say is a placeholder."""


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
    parts = []

    if plan.finish:
        parts += [session.rejections_text(result.changes, language), not_sold, session.readback(language)]
    elif result.changes or prices or not_sold:
        parts += [not_sold, session.changes_text(result.changes, language), prices]
    elif not (closing and result.payment_set):
        # nothing about the order happened: the model's own words, with a read-back where it asked for one
        text = say.replace("[ORDER]", session.readback(language)).replace("[LINES]", "")
        return " ".join(_PLACEHOLDER.sub("", text).split())

    if closing and result.payment_set:
        parts.append(closing)
    elif plan.finish and not session.is_empty and session.payment is None:
        parts.append(SAY[lang]["pay"])
    elif not plan.finish:
        parts.append(SAY[lang]["more"])
    return " ".join(" ".join(p for p in parts if p).split())
