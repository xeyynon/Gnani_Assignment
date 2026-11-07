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

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from . import store

log = logging.getLogger("order_session")

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
        "more": "Anything else?", "what": "What would you like to order?", "pay": "How would you like to pay: cash, UPI or credit?",
        "not_sold": "Sorry, we do not have {names}.",
        "credit_need_name": "Please tell me your name so I can check your credit.",
        "credit_ok": "{name}, your credit balance is {before} rupees. This order is {total} rupees, so it will be {after} rupees, within your limit of {limit} rupees.",
        "credit_over": "{name}, this order would take your credit balance to {after} rupees, above your limit of {limit} rupees. Please pay by cash or UPI, or reduce the order.",
        "credit_unknown": "I could not find you in the credit book.",
        "credit_balance": "{name}, you owe {balance} rupees. Your credit limit is {limit} rupees.",
        "credit_balance_clear": "{name}, you owe nothing right now. Your credit limit is {limit} rupees.",
    },
    "hi": {
        "added": "{lines} जोड़ दिया।", "updated": "बदल दिया: {lines}।", "removed": "{name} हटा दिया।",
        "unavailable": "{name} आज उपलब्ध नहीं है।", "unknown": "यह चीज़ हमारी सूची में नहीं मिली।",
        "bad_qty": "कृपया {name} की मात्रा दोबारा बताइए।", "not_in_order": "{name} आपके ऑर्डर में नहीं है।",
        "total": "अभी तक कुल {total} रुपये।", "order": "आपका ऑर्डर: {lines}। कुल {total} रुपये।",
        "empty": "अभी आपके ऑर्डर में कुछ नहीं है।", "price": "{name} {price} रुपये {per} है।",
        "more": "और कुछ चाहिए?", "what": "आपको क्या चाहिए?", "pay": "पेमेंट कैसे करेंगे: कैश, यूपीआई या उधार?",
        "not_sold": "माफ़ कीजिए, {names} हमारे पास नहीं है।",
        "credit_need_name": "कृपया अपना नाम बताइए ताकि मैं आपका उधार देख सकूँ।",
        "credit_ok": "{name}, आपका उधार {before} रुपये है। यह ऑर्डर {total} रुपये का है, तो कुल {after} रुपये होगा, आपकी {limit} रुपये की सीमा के अंदर।",
        "credit_over": "{name}, इस ऑर्डर से आपका उधार {after} रुपये हो जाएगा, जो आपकी {limit} रुपये की सीमा से ज़्यादा है। कृपया कैश या यूपीआई से भुगतान कीजिए, या ऑर्डर कम कीजिए।",
        "credit_unknown": "आपका नाम उधार की बही में नहीं मिला।",
        "credit_balance": "{name}, आपका {balance} रुपये उधार बाकी है। आपकी उधार सीमा {limit} रुपये है।",
        "credit_balance_clear": "{name}, अभी आपका कोई उधार बाकी नहीं है। आपकी उधार सीमा {limit} रुपये है।",
    },
    "te": {
        "added": "{lines} జోడించాను.", "updated": "మార్చాను: {lines}.", "removed": "{name} తీసేశాను.",
        "unavailable": "{name} ఈరోజు అందుబాటులో లేదు.", "unknown": "ఆ వస్తువు మా జాబితాలో కనిపించలేదు.",
        "bad_qty": "దయచేసి {name} ఎంత కావాలో మళ్ళీ చెప్పండి.", "not_in_order": "{name} మీ ఆర్డర్‌లో లేదు.",
        "total": "ఇప్పటి వరకు మొత్తం {total} రూపాయలు.", "order": "మీ ఆర్డర్: {lines}. మొత్తం {total} రూపాయలు.",
        "empty": "మీ ఆర్డర్‌లో ఇంకా ఏమీ లేదు.", "price": "{name} {per} {price} రూపాయలు.",
        "more": "ఇంకా ఏదైనా కావాలా?", "what": "మీకు ఏమి కావాలి?", "pay": "చెల్లింపు ఎలా చేస్తారు: నగదు, యూపీఐ లేదా అప్పు?",
        "not_sold": "క్షమించండి, {names} మా దగ్గర లేదు.",
        "credit_need_name": "దయచేసి మీ పేరు చెప్పండి, మీ అప్పు చూస్తాను.",
        "credit_ok": "{name}, మీ అప్పు {before} రూపాయలు. ఈ ఆర్డర్ {total} రూపాయలు, కాబట్టి మొత్తం {after} రూపాయలు అవుతుంది, మీ {limit} రూపాయల పరిమితి లోపే.",
        "credit_over": "{name}, ఈ ఆర్డర్‌తో మీ అప్పు {after} రూపాయలు అవుతుంది, మీ {limit} రూపాయల పరిమితి కంటే ఎక్కువ. దయచేసి నగదు లేదా యూపీఐతో చెల్లించండి, లేదా ఆర్డర్ తగ్గించండి.",
        "credit_unknown": "అప్పు పుస్తకంలో మీ పేరు కనిపించలేదు.",
        "credit_balance": "{name}, మీరు {balance} రూపాయలు బాకీ ఉన్నారు. మీ అప్పు పరిమితి {limit} రూపాయలు.",
        "credit_balance_clear": "{name}, ప్రస్తుతం మీకు బాకీ ఏమీ లేదు. మీ అప్పు పరిమితి {limit} రూపాయలు.",
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
    credit_events: list = field(default_factory=list)       # what the credit book found this turn (see _credit_update)


def _decimal(raw):
    if isinstance(raw, bool):
        return None
    try:
        q = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    return q if q.is_finite() and q > 0 else None


def _op_key(op) -> tuple:
    q = _decimal(op.get("qty")) if op.get("qty") is not None else None
    return (str(op.get("op", "")).strip().lower(), str(op.get("sku", "")).strip(), None if q is None else q.normalize())


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
                 listener=None, credit=None):
        self.shop = shop
        self._items = {it["sku"]: it for it in items}
        self._now = now or datetime.now(store.IST)
        self.call_id = call_id or self._now.strftime("%Y%m%d-%H%M%S") + f"-{self._now.microsecond // 1000:03d}"     # ms: two calls in one second must not overwrite each other
        self.lines: dict = {}               # sku -> Decimal quantity, in the order they were first added
        self._seen_ops: set = set()         # (op, sku, qty) of every change made so far, to recognise a model that repeats them
        self.payment: str | None = None
        self.customer: str | None = None
        self.delivery: str | None = None
        self.language = "en-IN"
        self.finished = False               # the caller said that is all
        self.closed = False
        self._lock = threading.RLock()
        self.listener = listener            # called with the order as the call page shows it, after each change
        self.credit = credit                # credit.CreditBook of the shop, or None if the shop keeps no credit book
        self.credit_state: str | None = None        # approved | over_limit | unknown | need_name, while paying by udhaar
        self.credit_id: str | None = None           # the customer the spoken name was matched to
        self.balance_before: int | None = None
        self.balance_after: int | None = None
        self._credit_sig = None
        self._balance_wanted = False

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
              language=None, balance_query=False) -> TurnResult:
        with self._lock:
            if self.closed:
                return TurnResult([], closed=True)
            if self._is_replay_on_payment_turn(ops, payment):
                log.warning("[ORDER] the model re-added the whole order on a payment turn (B-30); those lines are ignored")
                ops = []
            changes = []
            for op in (ops or []):
                c = self._apply_one(op)
                if c is None:
                    continue
                changes.append(c)
                if c.kind in ("added", "updated", "removed"):
                    self._seen_ops.add(_op_key(op))
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
            credit_events = self._credit_update(balance_query)
            listener, event = self.listener, self.event()
        if listener is not None and any(c.kind in ("added", "updated", "removed") for c in changes):
            try:
                listener(event)
            except Exception:
                pass                         # showing the order on the page must never break the call
        return TurnResult(changes, payment_set=self.payment is not None and self.payment != payment_before,
                          credit_events=credit_events)

    # ---- credit ----------------------------------------------------------------------------------------------------

    def _credit_update(self, balance_query: bool) -> list:
        """
        Called at the end of every turn, with the lock held. Looks the spoken name up in the credit book and says
        what changed since the last turn, as events: need_name, approved, over_limit, unknown (paying by udhaar), and
        balance, balance_unknown (the caller asked what they owe). An event is produced only when the situation
        changes, so the caller is not told the same thing every turn.
        """
        try:
            return self._credit_events(balance_query)
        except store.LedgerUnreadable as e:
            # The book cannot be trusted this turn: say nothing about balances and leave credit to the shopkeeper.
            log.warning(f"[CREDIT] the ledger is unreadable, credit stays with the shopkeeper: {e}")
            self.balance_before = self.balance_after = None
            self.credit_id, self._credit_sig = None, None
            if self.payment == "udhaar" and self.customer:
                self.credit_state = "unknown"
                return [{"kind": "unknown"}]
            return [{"kind": "balance_unknown"}] if self._balance_wanted and self.customer else []

    def _credit_events(self, balance_query) -> list:
        events = []
        if balance_query:
            self._balance_wanted = True
        if self.credit is None:
            return events
        cid = self.credit.find(self.customer) if self.customer else None
        self.credit_id = cid if self.customer else None
        if self._balance_wanted:
            if not self.customer:
                if self.payment != "udhaar":
                    events.append({"kind": "need_name"})
            else:
                self._balance_wanted = False
                events.append({"kind": "balance", "cid": cid} if cid else {"kind": "balance_unknown"})
        if self.payment == "udhaar":
            if not self.customer:
                state, sig = "need_name", ("need_name",)
            elif cid is None:
                state, sig = "unknown", ("unknown",)
            else:
                check = self.credit.check(cid, self.total())
                state = "approved" if check.ok else "over_limit"
                sig = (state, cid, self.total())
                self.balance_before, self.balance_after = (check.before, check.after) if check.ok else (None, None)
                if sig != self._credit_sig:
                    events.append({"kind": state, "cid": cid, "before": check.before, "after": check.after,
                                   "limit": check.limit, "total": self.total()})
            if state in ("need_name", "unknown") and sig != self._credit_sig:
                events.append({"kind": state})
            self._credit_sig = sig
            self.credit_state = state
            if state == "over_limit":                     # credit refused: the caller has to choose another way to pay
                self.payment, self.credit_state, self._credit_sig = None, None, None
                self.balance_before = self.balance_after = None
        else:
            self.credit_state, self._credit_sig = None, None
            self.balance_before = self.balance_after = None
        return events

    def credit_text(self, result: TurnResult, language) -> str:
        """The sentences for this turn's credit events, in the caller's language, figures from the book."""
        lang = lang_key(language)
        say, unit = SAY[lang], RUPEES[lang]
        out = []
        for e in result.credit_events:
            kind = e["kind"]
            if kind in ("need_name", "credit_need_name"):
                out.append(say["credit_need_name"])
            elif kind == "unknown" or kind == "balance_unknown":
                out.append(say["credit_unknown"])
            elif kind in ("approved", "over_limit"):
                name = self.credit.name(e["cid"], lang)
                key = "credit_ok" if kind == "approved" else "credit_over"
                out.append(say[key].format(name=name, before=e["before"], total=e["total"], after=e["after"], limit=e["limit"]))
            elif kind == "balance":
                name = self.credit.name(e["cid"], lang)
                try:
                    balance, limit = self.credit.balance(e["cid"]), self.credit.limit(e["cid"])
                except store.LedgerUnreadable:
                    out.append(say["credit_unknown"])
                    continue
                out.append(say["credit_balance" if balance else "credit_balance_clear"].format(name=name, balance=balance, limit=limit))
        return " ".join(out)

    def drop_replayed_ops(self, ops: list, named: set, has_quantity: bool) -> tuple:
        """
        Splits the model's ops into (kept, dropped). The model sometimes copies the changes of an earlier turn into
        the note for a later one (B-30), which doubles an order: on a live run "Bas itna hi" (that is all) added the
        same two packets again, and "UPI" added them a third time. The instructions say never to, and the larger
        model mostly obeys, but the smaller one often does not, so this is checked in code. The caller's own words
        are the only authority for a change:
          - an op for a product the caller just named (`named`: SKUs) is always kept;
          - any other op is dropped if it is exactly a change already made on an earlier turn (a replay);
          - if the sentence names no product and gives no quantity, a new add or set is dropped too (nothing was said
            that could change an item); a remove is kept, because "take that out" names nothing.
        Ops for SKUs the shop does not have are kept: applying them gives the usual "I could not find" answer.
        """
        kept, dropped = [], []
        nothing_said = not named and not has_quantity
        with self._lock:
            for op in ops or []:
                kind = str(op.get("op", "")).strip().lower() if isinstance(op, dict) else ""
                sku = str(op.get("sku", "")).strip() if isinstance(op, dict) else ""
                if sku in named or sku not in self._items or kind not in ("add", "set", "remove"):
                    kept.append(op)
                elif _op_key(op) in self._seen_ops or (nothing_said and kind in ("add", "set")):
                    dropped.append(op)
                else:
                    kept.append(op)
        return kept, dropped

    def _is_replay_on_payment_turn(self, ops, payment) -> bool:
        """
        The caller has just chosen how to pay and the model's note adds every line of the order again with the
        same quantity: that doubles the order (B-30, seen once on a live call: 4 kg sugar and 16 L oil became twice
        as much). A real "add all of it again" is not something a shopper says while paying, so such a note is dropped.
        Any other ops on a payment turn are applied as usual.
        """
        if self.payment is not None or payment is None or len(self.lines) < 2 or not ops:
            return False                                 # one line only: "one more maggi, cash" looks exactly like a replay
        adds = {}
        for op in ops:
            if not isinstance(op, dict) or str(op.get("op", "")).strip().lower() != "add":
                return False
            q = _decimal(op.get("qty"))
            sku = str(op.get("sku", "")).strip()
            if q is None or sku not in self.lines or sku in adds:
                return False
            adds[sku] = q
        return adds == {sku: q for sku, q in self.lines.items()}

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
            if op.get("qty") is None:
                del self.lines[sku]                     # no quantity said: the whole line goes
                return Change("removed", sku)
            q = _decimal(op.get("qty"))
            if q is None:
                return Change("bad_qty", sku)           # a quantity that is zero, negative or not a number never deletes a line
            if q < current:
                left = current - q
                if not _valid_qty(item["unit"], left):
                    return Change("bad_qty", sku)       # what is left must be a quantity an add would accept (no 2.5 packets)
                self.lines[sku] = left
                return Change("updated", sku, left, self._line_total(sku, left))
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
            updated = [c for c in updated if c.sku in self.lines]       # a line updated and then removed in one note is only "removed"
            if updated:
                out.append(say["updated"].format(
                    lines=", ".join(self._describe(c.sku, self.lines[c.sku], lang) for c in updated)))
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
            return "confirmed" if self.credit_state == "approved" else "credit_pending"     # else the shopkeeper confirms
        return "confirmed" if self.payment in ("cash", "upi") else "incomplete"

    def _customer_for_record(self):
        """The credit book's name for the customer when one was matched, else the name as heard."""
        if self.credit is not None and self.credit_id:
            return self.credit.name(self.credit_id, "en")
        return self.customer

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
                    "status": self.status(), "customer": self._customer_for_record(), "items": items, "total": self.total(),
                    "payment": self.payment or "", "delivery": self.delivery or "home delivery",
                    "balance_before": self.balance_before if self.credit_state == "approved" else None,
                    "balance_after": self.balance_after if self.credit_state == "approved" else None,
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

    def _credit_precheck(self) -> bool:
        """At hang-up, with the lock held: re-check the limit against the book as it is now (another call may have used
        credit since). True when the order should be charged to the customer once its file is written. If the check no
        longer passes, or the book cannot be read, the order stays pending for the shopkeeper."""
        if self.credit is None or self.payment != "udhaar" or self.credit_state != "approved" or not self.lines:
            return False
        try:
            check = self.credit.check(self.credit_id, self.total())
        except Exception as e:
            log.warning(f"[CREDIT] could not re-check the limit, the order stays pending: {e}")
            self.credit_state, self.balance_before, self.balance_after = "unknown", None, None
            return False
        if not check.ok:
            self.credit_state, self.balance_before, self.balance_after = "unknown", None, None
            return False
        self.balance_before, self.balance_after = check.before, check.after
        return True

    def _credit_charge(self) -> bool:
        """Add the order to the customer's balance. Done after the order file is safely written, so a failed write can
        never leave a customer charged for an order that no one can find. False if the ledger could not be written."""
        try:
            self.credit.record(self.credit_id, self.call_id, self.total(), self._now)
            return True
        except Exception as e:
            log.warning(f"[CREDIT] the ledger could not be written, the order stays pending: {e}")
            return False

    def close(self, root=None):
        """End of the call: write the order (if any) and refuse further changes. Returns the record or None."""
        with self._lock:
            if self.closed:
                return None
            self.closed = True
            charge = self._credit_precheck()
            record = self.to_record()
            text = self.to_text()
        if record is not None:
            store.write_order(self.shop, record, root)
            store.write_order_text(self.shop, self.call_id, text, root)
        if charge and not self._credit_charge():
            with self._lock:                                  # not charged: rewrite the order as waiting for the shopkeeper
                self.credit_state, self.balance_before, self.balance_after = "unknown", None, None
                record = self.to_record()
                text = self.to_text()
            store.write_order(self.shop, record, root)
            store.write_order_text(self.shop, self.call_id, text, root)
        return record
