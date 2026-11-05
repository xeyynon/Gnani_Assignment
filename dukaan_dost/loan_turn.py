"""
loan_turn.py

One turn of a loan-guidance call, between the language model and loan_session.py (see that file for why).

  detect(text)       does the caller want loan guidance? A keyword check in code, no model call, so it costs no
                     tokens and cannot hallucinate. A miss just leaves the call in the shop-order flow.
  prompt_section()   the instructions that make the model return one JSON object: the amount as rupees in digits,
                     whether it is the caller's own money or the whole project cost, the business and the place.
  parse_plan()       reads that object defensively.
  compose()          the reply: always the code's sentences. The model's own words are used only for a plain
                     question about the schemes, and never when they contain a digit (a wrong figure spoken
                     confidently is the failure to avoid).
"""

import json
import logging
import re
from dataclasses import dataclass

from .order_turn import extract_json

log = logging.getLogger("loan_turn")

# Words that mean "I want a loan / business funding". Hindi and Telugu words are written as callers and
# Prisma write them. Telugu అప్పు (debt, also "on credit") is NOT here: in a shop it means udhaar.
_LOAN_WORDS = [
    r"\bloans?\b", r"\bemi\b", r"\binterest\b", r"\bmudra\b", r"\budyami\b", r"\bsubsidy\b", r"\bmoratorium\b",
    r"\bkarz\w*", r"\bkarj\w*", r"\bbyaj\b", r"\bvyapar\b", r"\bbusiness\b", r"\bstart (?:a|my) (?:shop|business)\b",
    r"\bfund(?:ing)?\b", r"\binvest\w*", r"लोन", r"कर्ज", r"कर्ज़", r"ऋण", r"ब्याज", r"किस्त", r"कारोबार", r"व्यापार",
    r"बिज़नेस", r"बिजनेस", r"दुकान खोल", r"निवेश", r"योजना", r"లోన్", r"రుణం", r"రుణ", r"వడ్డీ", r"వ్యాపారం", r"బిజినెస్",
    r"పెట్టుబడి", r"పథకం", r"ఈఎంఐ", r"కిస్తీ", r"కిస్తు", r"వాయిదా",
]
_LOAN_RE = re.compile("|".join(_LOAN_WORDS), re.IGNORECASE)


def detect(text: str) -> bool:
    return bool(text) and _LOAN_RE.search(text) is not None


def prompt_section() -> str:
    return """LOAN MODE. The caller wants guidance on a small-business loan. You never work out or say any loan figure: the system does, from the amount you report. Your whole answer, to every message, is ONE JSON object and nothing else:
{"amount": <number or null>, "amount_kind": "margin_money" | "project_cost" | null, "business": <string or null>, "place": <string or null>, "say": ""}
- amount: the rupee amount the caller just said, as a plain number in rupees with no commas. Convert Indian units: 1 lakh = 100000, 1 crore = 10000000, 1 hazaar / hajar / हज़ार / వేలు = 1000, so 50 hazaar = 50000, dedh lakh = 150000, 2.5 lakh = 250000, saade teen lakh = 350000, paanch lakh = 500000. null if no amount was said in the LAST message.
- amount_kind: "margin_money" if the caller means their own money or what they can invest or put in themselves (mere paas, main laga sakta hoon, nijanga petagalanu); "project_cost" if they mean what the whole shop or project will cost. null if it is not clear.
- business: the kind of business (kirana, tea stall, dairy, tailoring), in English letters, if said. place: the town or village, if said.
- say: leave it "" unless the caller asked a plain question about the schemes that has no number in the answer (what is a moratorium, how do I apply). Then answer in the caller's language in one short sentence with NO digits. Never state an amount, rate, instalment or period.
Examples (caller, then JSON):
"mujhe dukaan kholni hai, mere paas ek lakh hai" -> {"amount": 100000, "amount_kind": "margin_money", "business": "shop", "place": null, "say": ""}
"project ka kharcha dedh lakh hoga" -> {"amount": 150000, "amount_kind": "project_cost", "business": null, "place": null, "say": ""}
"I want a loan for a tea stall in Kurnool" -> {"amount": null, "amount_kind": null, "business": "tea stall", "place": "Kurnool", "say": ""}
"50 hazaar" -> {"amount": 50000, "amount_kind": null, "business": null, "place": null, "say": ""}"""


SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": ["number", "null"]},
        "amount_kind": {"type": ["string", "null"], "enum": ["margin_money", "project_cost", None]},
        "business": {"type": ["string", "null"]},
        "place": {"type": ["string", "null"]},
        "say": {"type": "string"}},
    "required": ["amount", "amount_kind", "business", "place", "say"],
    "additionalProperties": False,
}


@dataclass
class LoanPlan:
    amount: object = None
    kind: str | None = None
    business: str | None = None
    place: str | None = None
    say: str = ""


def parse_plan(text: str) -> LoanPlan | None:
    obj = extract_json(text)
    if obj is None:
        return None
    amount = obj.get("amount")
    return LoanPlan(
        amount=amount if isinstance(amount, (int, float)) and not isinstance(amount, bool) else None,
        kind=obj.get("amount_kind") if obj.get("amount_kind") in ("margin_money", "project_cost") else None,
        business=obj.get("business") if isinstance(obj.get("business"), str) else None,
        place=obj.get("place") if isinstance(obj.get("place"), str) else None,
        say=obj.get("say") if isinstance(obj.get("say"), str) else "",
    )


def compose(plan: LoanPlan, result, session, language) -> str:
    """The reply: the code's sentences, plus the model's words only for a digit-free question about the schemes."""
    text = session.text(result, language)
    say = " ".join(plan.say.split())
    if say and not re.search(r"\d", say) and result.status in ("ask_amount", "ask_kind") and plan.amount is None:
        return f"{say} {text}"
    if say and re.search(r"\d", say):
        log.warning(f"[LOAN] the model put a number in its own words, dropped: {say!r}")
    return text
