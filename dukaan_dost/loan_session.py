"""
loan_session.py

Udyami loan guidance on one call (DEC-027). Same division of labour as the order flow: the language model
only reads the caller's words into a number (loan_turn.py); this code checks it, asks for what is missing, works
the figures out with loan_calculator.quote(), and writes every sentence the caller hears, so no figure is ever
the model's. The record goes to orders/<shop>/loan_<call_id>.json for the dashboard.

How big numbers are spoken (found 2026-11-03 by playing sentences through Timbre and reading them back with
Prisma): Timbre reads a plain six or seven digit number wrongly in Hindi and Telugu ("100000" came back as ten
million, "4500000" as 45 million). "1 लाख", "45 लక్షల" and "45 lakh" all came back right. So amounts from one
lakh up are spoken in lakh and crore words, and only amounts under one lakh are spoken as plain digits.

Every figure is indicative (the problem statement does not give the instalment rule, DEC-028) and the spoken
answer says so.
"""

import os
import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from . import loan_calculator, store
from .order_session import lang_key

MAX_AMOUNT = 100 * 10_000_000            # 100 crore: anything above is a mis-hearing, not a project
MIN_AMOUNT = 1_000                       # under a thousand rupees is a mis-hearing too ("0.4" or "1" would quote a loan of 9 rupees)
LAKH = 100_000
CRORE = 10_000_000

KINDS = ("margin_money", "project_cost")

RUPEES = {"en": "rupees", "hi": "रुपये", "te": "రూపాయలు"}
LAKH_WORD = {"en": ("lakh", "lakh"), "hi": ("लाख", "लाख"), "te": ("లక్ష", "లక్షల")}        # (one, more than one)
CRORE_WORD = {"en": ("crore", "crore"), "hi": ("करोड़", "करोड़"), "te": ("కోటి", "కోట్ల")}


def _plain(n: Decimal) -> str:
    return format(n.normalize(), "f")


def _key(language) -> str:
    """'hi-IN' -> 'hi'; an already short key ('hi') is kept."""
    return language if language in RUPEES else lang_key(language)


def spoken_amount(amount: int, language) -> str:
    """'90000 rupees', '1 lakh rupees', '1.35 lakh rupees', '1 lakh 12500 rupees', '2 crore rupees'."""
    lang = _key(language)
    amount = int(amount)
    unit = RUPEES[lang]
    if amount < LAKH:
        return f"{amount} {unit}"
    if amount >= CRORE:
        whole, rest = divmod(amount, CRORE)
        if rest == 0:
            word = CRORE_WORD[lang][0 if whole == 1 else 1]
            return f"{whole} {word} {unit}"
        if rest % LAKH == 0:                                    # 1.5 crore, 2.25 crore
            value = Decimal(amount) / CRORE
            return f"{_plain(value)} {CRORE_WORD[lang][1]} {unit}"
        # not a tidy number of lakhs: say it in lakhs instead
    lakhs, rest = divmod(amount, LAKH)
    word = LAKH_WORD[lang][0 if lakhs == 1 else 1]
    if rest == 0:
        return f"{lakhs} {word} {unit}"
    if rest % 1000 == 0:                                         # whole thousands: 1.35 lakh
        return f"{_plain(Decimal(amount) / LAKH)} {LAKH_WORD[lang][1]} {unit}"
    return f"{lakhs} {word} {rest} {unit}"                       # 1 lakh 12500


SAY = {
    "en": {
        "ask_amount": "How much money can you put in yourself, or what will the whole project cost?",
        "ask_kind": "I heard {amount}. Is that your own money, or the whole project cost?",
        "heard_margin": "I heard {amount} as your own money, so a project of about {cost}.",
        "heard_cost": "I heard a project cost of {amount}, so you would put in {margin} yourself.",
        "quote": "Under the {scheme}, the agency could lend up to {loan} at {rate} percent a year. "
                 "After {moratorium} months of grace you would pay about {emi} a month for {months} months.",
        "limit": "Your own share would be {own}, because the loan is capped.",
        "approx": "These figures are approximate. If I misheard the amount, please tell me again.",
        "not_covered": "A project of about {cost} is above the {limit} these schemes cover, so I cannot give a loan figure for it.",
        "bad_amount": "I could not understand that amount. Please say it again, for example fifty thousand or one lakh.",
    },
    "hi": {
        "ask_amount": "आप अपनी तरफ़ से कितना पैसा लगा सकते हैं, या पूरे प्रोजेक्ट की लागत कितनी होगी?",
        "ask_kind": "मैंने {amount} सुना। क्या यह आपका अपना पैसा है, या पूरे प्रोजेक्ट की लागत?",
        "heard_margin": "मैंने {amount} आपका अपना पैसा सुना, यानी लगभग {cost} का प्रोजेक्ट।",
        "heard_cost": "मैंने {amount} प्रोजेक्ट की लागत सुनी, यानी आपको अपनी तरफ़ से {margin} लगाने होंगे।",
        "quote": "{scheme} के तहत {loan} तक का कर्ज़ मिल सकता है, {rate} प्रतिशत सालाना ब्याज पर। "
                 "{moratorium} महीने की छूट के बाद लगभग {emi} महीने की किस्त, {months} महीने तक।",
        "limit": "कर्ज़ की सीमा होने से आपका अपना हिस्सा {own} होगा।",
        "approx": "ये आँकड़े अंदाज़न हैं। अगर रकम ग़लत सुनी हो तो कृपया दोबारा बताइए।",
        "not_covered": "लगभग {cost} का प्रोजेक्ट इन योजनाओं की {limit} की सीमा से ऊपर है, इसलिए मैं इसका कर्ज़ नहीं बता सकता।",
        "bad_amount": "मैं वह रकम समझ नहीं पाया। कृपया दोबारा बताइए, जैसे पचास हज़ार या एक लाख।",
    },
    "te": {
        "ask_amount": "మీరు మీ వైపు నుంచి ఎంత డబ్బు పెట్టగలరు, లేదా మొత్తం ప్రాజెక్ట్ ఖర్చు ఎంత అవుతుంది?",
        "ask_kind": "నాకు {amount} వినిపించింది. అది మీ సొంత డబ్బా, లేదా మొత్తం ప్రాజెక్ట్ ఖర్చా?",
        "heard_margin": "{amount} మీ సొంత డబ్బుగా విన్నాను, అంటే సుమారు {cost} ప్రాజెక్ట్.",
        "heard_cost": "ప్రాజెక్ట్ ఖర్చు {amount} అని విన్నాను, అంటే మీరు సొంతంగా {margin} పెట్టాలి.",
        "quote": "{scheme} కింద {loan} వరకు రుణం దొరకవచ్చు, సంవత్సరానికి {rate} శాతం వడ్డీతో. "
                 "{moratorium} నెలల విరామం తర్వాత నెలకు సుమారు {emi} వాయిదా, {months} నెలల పాటు.",
        "limit": "రుణ పరిమితి వల్ల మీ సొంత వాటా {own} అవుతుంది.",
        "approx": "ఈ లెక్కలు సుమారుగా ఉంటాయి. మొత్తం తప్పుగా విన్నట్లయితే దయచేసి మళ్ళీ చెప్పండి.",
        "not_covered": "సుమారు {cost} ప్రాజెక్ట్ ఈ పథకాల పరిమితి {limit} కంటే ఎక్కువ, కాబట్టి దానికి రుణం చెప్పలేను.",
        "bad_amount": "ఆ మొత్తం నాకు అర్థం కాలేదు. దయచేసి మళ్ళీ చెప్పండి, ఉదాహరణకు యాభై వేలు లేదా ఒక లక్ష.",
    },
}


@dataclass
class LoanResult:
    status: str          # quoted | ask_amount | ask_kind | not_covered | bad_amount | closed
    amount: int | None = None
    kind: str | None = None


def _amount_to_int(raw):
    """The amount as whole rupees, or None for anything that is not a sensible positive number."""
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        d = Decimal(str(raw).replace(",", "").strip())
    except Exception:
        return None
    if not d.is_finite() or d < MIN_AMOUNT or d > MAX_AMOUNT:
        return None
    return int(d.to_integral_value())


def _clean_text(raw, limit=40):
    if not isinstance(raw, str):
        return None
    text = " ".join(raw.replace("<", " ").replace(">", " ").split())[:limit]
    return text or None


class LoanSession:
    def __init__(self, shop: str, call_id: str | None = None, now: datetime | None = None, listener=None):
        self.shop = shop
        self.listener = listener             # called with the quote as the call page shows it, after each new quote
        self._now = now or datetime.now(store.IST)
        self.call_id = call_id or self._now.strftime("%Y%m%d-%H%M%S") + f"-{self._now.microsecond // 1000:03d}"
        self.active = False                  # the call has turned into a loan conversation
        self.language = "en-IN"
        self.business = None
        self.place = None
        self.quote = None                    # loan_calculator.LoanQuote of the latest amount understood
        self.kind = None                     # margin_money | project_cost
        self.heard_amount = None
        self.closed = False
        self._pending_amount = None          # an amount heard without saying what it is
        self._lock = threading.RLock()

    # ---- a turn --------------------------------------------------------------------------------------------------

    def apply(self, amount=None, kind=None, business=None, place=None, language=None) -> LoanResult:
        with self._lock:
            if self.closed:
                return LoanResult("closed")      # a turn still in flight after hang-up must not quote, show or save anything
            if language:
                self.language = language
            self.business = _clean_text(business) or self.business
            self.place = _clean_text(place) or self.place
            kind = kind if kind in KINDS else None
            value = _amount_to_int(amount)
            if amount is not None and value is None:
                return LoanResult("bad_amount")
            if value is None:
                if self._pending_amount and kind:                # the answer to "own money, or the whole project?"
                    value = self._pending_amount
                else:
                    return LoanResult("ask_kind" if self._pending_amount else "ask_amount",
                                      amount=self._pending_amount)
            if kind is None:
                self._pending_amount = value
                return LoanResult("ask_kind", amount=value)
            self._pending_amount = None
            margin = Decimal(value) if kind == "margin_money" else Decimal(value) * loan_calculator.MARGIN_SHARE
            try:
                quote = loan_calculator.quote(margin)
            except ValueError:
                return LoanResult("bad_amount")
            self.quote, self.kind, self.heard_amount = quote, kind, value
            listener, event = self.listener, self.event()
        if listener is not None:
            try:
                listener(event)
            except Exception:
                pass                         # showing the quote on the page must never break the call
        with self._lock:
            return LoanResult("quoted" if quote.covered else "not_covered", amount=value, kind=kind)

    # ---- speaking ----------------------------------------------------------------------------------------------------

    def text(self, result: LoanResult, language=None) -> str:
        lang = _key(language or self.language)
        say = SAY[lang]
        if result.status == "closed":
            return ""
        if result.status == "ask_amount":
            return say["ask_amount"]
        if result.status == "bad_amount":
            return say["bad_amount"]
        if result.status == "ask_kind":
            return say["ask_kind"].format(amount=spoken_amount(result.amount, lang))
        q = self.quote
        cost = spoken_amount(q.project_cost, lang)
        if result.status == "not_covered":
            return say["not_covered"].format(cost=cost, limit=spoken_amount(int(loan_calculator.TERM_LOAN.max_project_cost), lang))
        heard = (say["heard_margin"].format(amount=spoken_amount(self.heard_amount, lang), cost=cost)
                 if self.kind == "margin_money" else
                 say["heard_cost"].format(amount=spoken_amount(self.heard_amount, lang), margin=spoken_amount(q.margin_money, lang)))
        main = say["quote"].format(
            scheme=q.scheme.name, loan=spoken_amount(q.loan_amount, lang), rate=_plain(q.scheme.annual_rate_pct),
            moratorium=q.moratorium_months, emi=spoken_amount(q.monthly_instalment, lang), months=q.repayment_months)
        parts = [heard, main]
        if q.own_contribution > q.margin_money:                  # the cap binds: the caller pays more than 10 percent
            parts.append(say["limit"].format(own=spoken_amount(q.own_contribution, lang)))
        parts.append(say["approx"])
        return " ".join(parts)

    def event(self) -> dict:
        """The latest quote as the call page shows it (figures from the calculator, never from the model)."""
        with self._lock:
            q = self.quote.to_dict() if self.quote is not None else {}
            return {"type": "loan", "heard_amount": self.heard_amount, "kind": self.kind,
                    "business": self.business or "", "place": self.place or "", **q}

    # ---- the record ------------------------------------------------------------------------------------------------------

    def to_record(self):
        with self._lock:
            if self.quote is None:
                return None
            return {"call_id": self.call_id, "time": self._now.isoformat(), "language": self.language,
                    "business": self.business or "", "place": self.place or "",
                    "synthetic": os.environ.get("ORDER_SYNTHETIC") == "1", **self.quote.to_dict()}

    def close(self, root=None):
        with self._lock:
            if self.closed:
                return None
            self.closed = True
            record = self.to_record()
        if record is not None:
            store.write_loan(self.shop, record, root)
        return record
