"""
order_session.py

The order being taken on one call, and all the money. The language model never adds anything
up: it only says WHICH items and HOW MANY the caller asked for (order_turn.py). This code checks
every item against the shop's stock list, keeps the order, works out each line and the total,
and writes the sentences that state them, in the caller's language, so the numbers a caller
hears are exactly the numbers on the shopkeeper's dashboard.

Rules (research method M4; bug B-15):
  - An item must be in stock.json. Unknown items and items out of stock are refused.
  - Quantity is in the item's own unit. kg and litre: multiples of 0.25 up to 25. Packet, piece,
    bar, bottle, bag, loaf: whole numbers up to 24. Anything else is refused and the caller is asked again.
  - A line is price x quantity, rounded to whole rupees (half up); the total is the sum of the
    rounded lines. So a line on the screen is always what was said aloud.

Thread-safety: the processor thread applies turns, the watchdog thread closes the order at
hang-up. Every method takes the object's lock.
"""

import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from . import store

MEASURED_UNITS = {"kg", "litre"}
MAX_MEASURED = Decimal("25")
MAX_COUNT = Decimal("24")
STEP = Decimal("0.25")

PAYMENTS = ("cash", "upi", "udhaar")
_PAYMENT_WORDS = {"cash": "cash", "cod": "cash", "upi": "upi", "udhaar": "udhaar", "credit": "udhaar",
                  "uddhar": "udhaar", "udhar": "udhaar"}


def lang_key(language_code) -> str:
    return {"en-in": "en", "hi-in": "hi", "te-in": "te"}.get((language_code or "").lower(), "en")


# ---------------------------------------------------------------------------------------------
# The words the code speaks. Hindi and Telugu were written by the assistant and need a
# native-speaker check (bug B-16). {name} comes from stock.json in the same language.
# ---------------------------------------------------------------------------------------------

UNIT_WORDS = {
    "en": {"kg": "kilo", "litre": "litre", "packet": "packet", "bottle": "bottle", "bag": "bag", "bar": "bar"},
    "hi": {"kg": "किलो", "litre": "लीटर", "packet": "पैकेट", "bottle": "बोतल", "bag": "बैग", "bar": "बार"},
    "te": {"kg": "కిలో", "litre": "లీటర్", "packet": "ప్యాకెట్", "bottle": "బాటిల్", "bag": "బ్యాగ్", "bar": "బార్"},
}   # piece and loaf have no unit word: "2 Bread", not "2 loaf Bread"

RUPEES = {"en": "rupees", "hi": "रुपये", "te": "రూపాయలు"}

# "per kilo" and so on, for answering "what does it cost?". Pieces and loaves are sold singly.
PER_UNIT = {
    "en": {"kg": "per kilo", "litre": "per litre", "packet": "per packet", "bottle": "per bottle", "bag": "per bag",
           "bar": "per bar", "piece": "each", "loaf": "each"},
    "hi": {"kg": "प्रति किलो", "litre": "प्रति लीटर", "packet": "प्रति पैकेट", "bottle": "प्रति बोतल",
           "bag": "प्रति बैग", "bar": "प्रति बार", "piece": "प्रति नग", "loaf": "प्रति नग"},
    "te": {"kg": "కిలోకి", "litre": "లీటర్‌కి", "packet": "ప్యాకెట్‌కి", "bottle": "బాటిల్‌కి", "bag": "బ్యాగ్‌కి",
           "bar": "బార్‌కి", "piece": "ఒక్కటి", "loaf": "ఒక్కటి"},
}

SAY = {
    "en": {
        "added": "Added {lines}.", "updated": "Updated: {lines}.", "removed": "Removed {name}.",
        "unavailable": "{name} is not available today.", "unknown": "I could not find that item in our list.",
        "bad_qty": "Please tell me the quantity for {name} again.", "not_in_order": "{name} is not in your order.",
        "total": "Total so far {total} rupees.", "order": "Your order: {lines}. Total {total} rupees.",
        "empty": "Nothing in your order yet.", "price": "{name} is {price} rupees {per}.",
        "more": "Anything else?", "pay": "How would you like to pay: cash, UPI or credit?",
        "not_sold": "Sorry, we do not have {names}.",
    },
    "hi": {
        "added": "{lines} जोड़ दिया।", "updated": "बदल दिया: {lines}।", "removed": "{name} हटा दिया।",
        "unavailable": "{name} आज उपलब्ध नहीं है।", "unknown": "यह चीज़ हमारी सूची में नहीं मिली।",
        "bad_qty": "कृपया {name} की मात्रा दोबारा बताइए।", "not_in_order": "{name} आपके ऑर्डर में नहीं है।",
        "total": "अभी तक कुल {total} रुपये।", "order": "आपका ऑर्डर: {lines}। कुल {total} रुपये।",
        "empty": "अभी आपके ऑर्डर में कुछ नहीं है।", "price": "{name} {price} रुपये {per} है।",
        "more": "और कुछ चाहिए?", "pay": "पेमेंट कैसे करेंगे: कैश, यूपीआई या उधार?",
        "not_sold": "माफ़ कीजिए, {names} हमारे पास नहीं है।",
    },
    "te": {
        "added": "{lines} జోడించాను.", "updated": "మార్చాను: {lines}.", "removed": "{name} తీసేశాను.",
        "unavailable": "{name} ఈరోజు అందుబాటులో లేదు.", "unknown": "ఆ వస్తువు మా జాబితాలో కనిపించలేదు.",
        "bad_qty": "దయచేసి {name} ఎంత కావాలో మళ్ళీ చెప్పండి.", "not_in_order": "{name} మీ ఆర్డర్‌లో లేదు.",
        "total": "ఇప్పటి వరకు మొత్తం {total} రూపాయలు.", "order": "మీ ఆర్డర్: {lines}. మొత్తం {total} రూపాయలు.",
        "empty": "మీ ఆర్డర్‌లో ఇంకా ఏమీ లేదు.", "price": "{name} {per} {price} రూపాయలు.",
        "more": "ఇంకా ఏదైనా కావాలా?", "pay": "చెల్లింపు ఎలా చేస్తారు: నగదు, యూపీఐ లేదా అప్పు?",
        "not_sold": "క్షమించండి, {names} మా దగ్గర లేదు.",
    },
}


@dataclass
class Change:
    kind: str                 # added | updated | removed | unavailable | unknown | bad_qty | not_in_order
    sku: str = ""
    qty: Decimal | None = None
    line_total: int | None = None


@dataclass
class TurnResult:
    changes: list
    closed: bool = False
    payment_set: bool = False         # the caller chose how to pay on this turn


def _decimal(raw):
    if isinstance(raw, bool):
        return None
    try:
        q = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    return q if q.is_finite() and q > 0 else None


def _fmt_qty(q: Decimal) -> str:
    return format(q.normalize(), "f") if q != q.to_integral_value() else str(int(q))


def _valid_qty(unit: str, q: Decimal) -> bool:
    if unit in MEASURED_UNITS:
        return q <= MAX_MEASURED and q % STEP == 0
    return q <= MAX_COUNT and q == q.to_integral_value()


def _clean_name(name) -> str | None:
    if not isinstance(name, str):
        return None
    name = re.sub(r"[^\w\s.'\-ऀ-෿]", "", name).strip()[:40]
    return name or None


class OrderSession:
    def __init__(self, shop: str, items: list, call_id: str | None = None, now: datetime | None = None,
                 listener=None):
        self.shop = shop
        self._items = {it["sku"]: it for it in items}
        self._now = now or datetime.now(store.IST)
        self.call_id = call_id or self._now.strftime("%Y%m%d-%H%M%S")
        self.lines: dict = {}               # sku -> Decimal quantity, in the order they were first added
        self.payment: str | None = None
        self.customer: str | None = None
        self.delivery: str | None = None
        self.language = "en-IN"
        self.finished = False               # the caller said that is all
        self.closed = False
        self._lock = threading.RLock()
        self.listener = listener            # called with the order as the call page shows it, after each change

    # ---- reading ------------------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return not self.lines

    def _line_total(self, sku: str, qty: Decimal) -> int:
        return int((Decimal(str(self._items[sku]["price"])) * qty).quantize(Decimal(1), ROUND_HALF_UP))

    def total(self) -> int:
        with self._lock:
            return sum(self._line_total(s, q) for s, q in self.lines.items())

    def _name(self, sku: str, lang: str) -> str:
        item = self._items.get(sku)
        return item["name"][lang] if item else sku

    def _describe(self, sku: str, qty: Decimal, lang: str) -> str:
        item = self._items[sku]
        unit_word = UNIT_WORDS[lang].get(item["unit"], "")
        if lang == "en" and unit_word and qty != 1 and unit_word != "kilo" and unit_word != "litre":
            unit_word += "s"
        parts = [_fmt_qty(qty)] + ([unit_word] if unit_word else []) + [item["name"][lang]]
        return f"{' '.join(parts)} {self._line_total(sku, qty)} {RUPEES[lang]}"

    def state_for_model(self) -> str:
        """The order so far, for the language model. No amounts: it must not repeat any."""
        with self._lock:
            if not self.lines:
                text = "CURRENT ORDER: empty."
            else:
                rows = [f"{i}. {sku} {self._items[sku]['name']['en']} {_fmt_qty(q)} {self._items[sku]['unit']}"
                        for i, (sku, q) in enumerate(self.lines.items(), 1)]
                text = "CURRENT ORDER:\n" + "\n".join(rows)
            known = []
            if self.payment:
                known.append(f"payment: {self.payment}")
            if self.customer:
                known.append(f"customer name: {self.customer}")
            if self.delivery:
                known.append(f"delivery: {self.delivery}")
            return text + (("\nAlready known: " + "; ".join(known) + ".") if known else "")

    # ---- changing -----------------------------------------------------------------------------

    def apply(self, ops: list, payment=None, customer=None, delivery=None, finish=False,
              language=None) -> TurnResult:
        with self._lock:
            if self.closed:
                return TurnResult([], closed=True)
            changes = [c for op in (ops or []) if (c := self._apply_one(op)) is not None]
            payment_before = self.payment
            if payment is not None:
                key = _PAYMENT_WORDS.get(str(payment).strip().lower())
                if key:
                    self.payment = key
            name = _clean_name(customer)
            if name:
                self.customer = name
            if delivery is not None:
                d = str(delivery).strip().lower()
                if d in ("home", "home delivery", "delivery"):
                    self.delivery = "home delivery"
                elif d in ("pickup", "pick up", "pick-up", "collect"):
                    self.delivery = "pickup"
            if finish:
                self.finished = True
            if language:
                self.language = language
            listener, event = self.listener, self.event()
        if listener is not None and any(c.kind in ("added", "updated", "removed") for c in changes):
            try:
                listener(event)
            except Exception:
                pass                         # showing the order on the page must never break the call
        return TurnResult(changes, payment_set=self.payment is not None and self.payment != payment_before)

    def _apply_one(self, op):
        if not isinstance(op, dict):
            return None
        kind = str(op.get("op", "")).strip().lower()
        sku = str(op.get("sku", "")).strip()
        item = self._items.get(sku)
        if kind not in ("add", "set", "remove"):
            return None
        if item is None:
            return Change("unknown", sku)
        current = self.lines.get(sku)

        if kind == "remove":
            if current is None:
                return Change("not_in_order", sku)
            q = _decimal(op.get("qty")) if op.get("qty") is not None else None
            if q is not None and q < current:
                self.lines[sku] = current - q
                return Change("updated", sku, current - q, self._line_total(sku, current - q))
            del self.lines[sku]
            return Change("removed", sku)

        if not item["in_stock"]:
            return Change("unavailable", sku)
        q = _decimal(op.get("qty"))
        if q is None:
            return Change("bad_qty", sku)
        new = q if kind == "set" or current is None else current + q
        if not _valid_qty(item["unit"], new) or not _valid_qty(item["unit"], q):
            return Change("bad_qty", sku)
        self.lines[sku] = new
        return Change("added" if current is None else "updated", sku, new, self._line_total(sku, new))

    # ---- speaking -------------------------------------------------------------------------------

    def changes_text(self, changes: list, language) -> str:
        """Sentences stating what this turn changed and refused, with the running total."""
        lang = lang_key(language)
        say = SAY[lang]
        with self._lock:
            added = [c for c in changes if c.kind == "added"]
            updated = [c for c in changes if c.kind == "updated"]
            out = []
            for c in changes:
                if c.kind in ("unavailable", "bad_qty", "removed", "not_in_order"):
                    out.append(say[c.kind].format(name=self._name(c.sku, lang)))
                elif c.kind == "unknown":
                    out.append(say["unknown"])
            if added:
                out.append(say["added"].format(lines=", ".join(self._describe(c.sku, c.qty, lang) for c in added)))
            if updated:
                out.append(say["updated"].format(
                    lines=", ".join(self._describe(c.sku, self.lines[c.sku], lang) for c in updated
                                    if c.sku in self.lines)))
            if self.lines and any(c.kind in ("added", "updated", "removed") for c in changes):
                out.append(say["total"].format(total=self.total()))
            return " ".join(s for s in out if s)

    def rejections_text(self, changes: list, language) -> str:
        """Only the refusals, for when the whole order is about to be read back anyway."""
        return self.changes_text([c for c in changes if c.kind in ("unavailable", "bad_qty", "unknown", "not_in_order")],
                                 language)

    def not_sold_text(self, names: list, language) -> str:
        """Tells the caller about things they asked for that the shop does not sell at all. The names are the
        caller's own words as the model heard them, kept short and plain."""
        clean = []
        for n in names or []:
            n = _clean_name(n)
            if n and n.lower() not in [c.lower() for c in clean]:
                clean.append(n)
        if not clean:
            return ""
        return SAY[lang_key(language)]["not_sold"].format(names=", ".join(clean[:4]))

    def prices_text(self, skus: list, language) -> str:
        """The list price of each item named, for a caller who asks what something costs. Prices come from
        the stock list, never from the model."""
        lang = lang_key(language)
        out = []
        for sku in skus or []:
            item = self._items.get(str(sku).strip())
            if item is None:
                continue
            price = item["price"]
            price = int(price) if float(price).is_integer() else price
            out.append(SAY[lang]["price"].format(name=item["name"][lang], price=price,
                                                 per=PER_UNIT[lang].get(item["unit"], "")).replace("  ", " "))
        return " ".join(out)

    def readback(self, language) -> str:
        lang = lang_key(language)
        with self._lock:
            if not self.lines:
                return SAY[lang]["empty"]
            lines = ", ".join(self._describe(s, q, lang) for s, q in self.lines.items())
            return SAY[lang]["order"].format(lines=lines, total=self.total())

    # ---- the record -------------------------------------------------------------------------------

    def event(self) -> dict:
        """The order as the caller's page shows it."""
        with self._lock:
            return {"type": "order", "total": self.total(),
                    "items": [{"name": self._items[s]["name"]["en"], "qty": float(q) if q % 1 else int(q),
                               "unit": self._items[s]["unit"], "line_total": self._line_total(s, q)}
                              for s, q in self.lines.items()]}

    def status(self) -> str:
        if self.payment == "udhaar":
            return "credit_pending"            # the shopkeeper still has to confirm the credit
        return "confirmed" if self.payment in ("cash", "upi") else "incomplete"

    def to_record(self) -> dict | None:
        """The order file for the dashboard (store.py), or None if nothing was ordered."""
        with self._lock:
            if not self.lines:
                return None
            items = []
            for sku, q in self.lines.items():
                price = self._items[sku]["price"]
                items.append({"sku": sku, "name": self._items[sku]["name"]["en"],
                              "qty": float(q) if q % 1 else int(q), "unit": self._items[sku]["unit"],
                              "unit_price": int(price) if float(price).is_integer() else price,
                              "line_total": self._line_total(sku, q)})
            return {"call_id": self.call_id, "time": self._now.isoformat(), "language": self.language,
                    "status": self.status(), "customer": self.customer, "items": items, "total": self.total(),
                    "payment": self.payment or "", "delivery": self.delivery or "home delivery",
                    "balance_before": None, "balance_after": None,
                    "synthetic": os.environ.get("ORDER_SYNTHETIC") == "1"}

    def to_text(self) -> str:
        r = self.to_record()
        if r is None:
            return "No items were ordered.\n"
        rows = [f"  {i['qty']:>5} {i['unit']:<7} {i['name']:<28} @ {i['unit_price']:>5} = {i['line_total']:>6}"
                for i in r["items"]]
        return "\n".join([
            f"Order {r['call_id']}   shop: {self.shop}   {r['time']}",
            f"Customer: {r['customer'] or 'not given'}   Language: {r['language']}",
            "Items:", *rows,
            f"Total: {r['total']} rupees",
            f"Payment: {r['payment'] or 'not chosen'}   Delivery: {r['delivery']}   Status: {r['status']}",
        ]) + "\n"

    def close(self, root=None):
        """End of the call: write the order (if any) and refuse further changes. Returns the record or None."""
        with self._lock:
            if self.closed:
                return None
            self.closed = True
            record = self.to_record()
            text = self.to_text()
        if record is not None:
            store.write_order(self.shop, record, root)
            store.write_order_text(self.shop, self.call_id, text, root)
        return record
