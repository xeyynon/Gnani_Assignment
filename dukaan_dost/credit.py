"""
credit.py

The udhaar (credit) book of one shop (DEC-026). Regular customers may buy on credit up to a limit; what they owe is
kept in orders/<shop>/ledger.json, the file the dashboard already reads (format in store.py). As with money in
orders, the language model never decides any of this: it passes on the name it heard, and this code finds the
customer, checks the limit and keeps the balance.

  customers   shops/<shop>/customers.json: made-up regular customers with a limit and an opening balance.
  find(name)  the customer a spoken name belongs to, or None. A name is matched by letter overlap, in whichever
              script it was written. A close call between two customers is treated as unknown: asking again or
              leaving the credit to the shopkeeper is better than putting a debt on the wrong person.
  check()     would this order stay within the customer's limit?
  record()    add an order to a customer's balance (written atomically, one entry per order).
"""

import json
import re
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from . import store

MATCH_MIN = 0.80          # similarity needed to call a heard name a known customer
MATCH_GAP = 0.10          # and how far ahead of the next customer it must be
_HONORIFICS = {"ji", "bhai", "bhaiya", "garu", "sir", "madam", "mr", "mrs", "ms", "anna", "akka", "amma", "uncle", "aunty", "sahab", "saheb",
               "जी", "भाई", "भैया", "साहब", "साहिब", "मैडम", "गारु", "గారు", "అన్న", "అక్క", "అమ్మ", "సార్"}      # said in whichever script the name is
_LOCK = threading.RLock()
_STRIP = dict.fromkeys(map(ord, "‌‍़"), None)


@dataclass(frozen=True)
class CreditCheck:
    ok: bool
    before: int
    after: int
    limit: int


def _norm(name: str) -> str:
    text = unicodedata.normalize("NFC", name or "").lower().translate(_STRIP)
    text = re.sub(r"[^\wऀ-෿\s]", " ", text).replace("।", " ")
    return " ".join(w for w in text.split() if w not in _HONORIFICS)


def load_customers(shop_dir) -> list:
    """The shop's customers.json, validated. [] if the shop has none; ValueError if it is malformed."""
    path = Path(shop_dir) / "customers.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    out, seen = [], set()
    for c in data["customers"]:
        cid = str(c["id"])
        if not re.fullmatch(r"[a-z0-9_-]{1,32}", cid) or cid in seen:
            raise ValueError(f"{path}: bad or repeated customer id {cid!r}")
        seen.add(cid)
        for lang in ("en", "hi", "te"):
            if not str(c["name"].get(lang, "")).strip():
                raise ValueError(f"{path}: {cid} has no {lang} name")
        if int(c["credit_limit"]) <= 0 or int(c["opening_balance"]) < 0:
            raise ValueError(f"{path}: {cid} has a bad limit or balance")
        out.append(c)
    return out


class CreditBook:
    def __init__(self, shop: str, customers: list, root=None):
        self.shop = shop
        self.root = root
        self.customers = {c["id"]: c for c in customers}
        self._variants = []                                    # (customer id, normalised name)
        for c in customers:
            for name in [*c["name"].values(), *c.get("aliases", [])]:
                norm = _norm(name)
                if norm:
                    self._variants.append((c["id"], norm))
        self._ensure_ledger()

    @classmethod
    def for_shop(cls, shop: str, shop_dir, root=None):
        """The shop's credit book, or None if the shop keeps none."""
        customers = load_customers(shop_dir)
        return cls(shop, customers, root) if customers else None

    # ---- the ledger file ---------------------------------------------------------------------------------------------

    def _ensure_ledger(self) -> None:
        """Seed the ledger from the customer list for customers it does not have yet. A ledger that exists but cannot be
        read raises store.LedgerUnreadable: re-seeding it would replace every real balance with its opening balance."""
        with _LOCK:
            ledger = store.read_ledger_strict(self.shop, self.root)
            changed = False
            for cid, c in self.customers.items():
                if cid not in ledger["customers"]:
                    ledger["customers"][cid] = {"name": c["name"]["en"], "balance": int(c["opening_balance"]),
                                                "credit_limit": int(c["credit_limit"]), "last_purchase": None,
                                                "promise_date": None, "entries": []}
                    changed = True
            if changed:
                store.write_ledger(self.shop, ledger, self.root)

    def _entry(self, cid: str):
        return store.read_ledger_strict(self.shop, self.root)["customers"].get(cid)

    def balance(self, cid: str) -> int:
        entry = self._entry(cid)
        if entry is None:
            raise store.LedgerUnreadable(f"{cid}: no entry in the ledger")      # a known customer always has one; never answer "owes nothing"
        return int(entry["balance"])

    def limit(self, cid: str) -> int:
        entry = self._entry(cid)
        return int(entry["credit_limit"]) if entry else int(self.customers[cid]["credit_limit"])

    def name(self, cid: str, language: str = "en") -> str:
        return self.customers[cid]["name"].get(language) or self.customers[cid]["name"]["en"]

    # ---- finding a customer ---------------------------------------------------------------------------------------------

    def find(self, heard: str):
        """The customer id a spoken name belongs to, or None when it matches nobody clearly."""
        query = _norm(heard)
        if not query or len(query) < 2:
            return None
        best = {}
        for cid, variant in self._variants:
            if len(query) <= 3 or len(variant) <= 3:
                score = 1.0 if query == variant else 0.0                   # very short names must match exactly
            elif query != variant and (query.startswith(variant) or variant.startswith(query)) and abs(len(query) - len(variant)) > 1:
                score = 0.0                                                # Venkatesh is not Venkat: a longer name that only begins with a known one
            else:
                score = SequenceMatcher(None, query, variant).ratio()
            if score > best.get(cid, 0.0):
                best[cid] = score
        ranked = sorted(best.items(), key=lambda kv: -kv[1])
        if not ranked or ranked[0][1] < MATCH_MIN:
            return None
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < MATCH_GAP:
            return None
        return ranked[0][0]

    # ---- limits and balances ----------------------------------------------------------------------------------------------

    def check(self, cid: str, amount: int) -> CreditCheck:
        before = self.balance(cid)
        after = before + int(amount)
        return CreditCheck(after <= self.limit(cid), before, after, self.limit(cid))

    def record(self, cid: str, call_id: str, amount: int, now: datetime | None = None, note: str = "order") -> int:
        """Add `amount` to the customer's balance and log it. Returns the new balance."""
        now = now or datetime.now(store.IST)
        with _LOCK:
            ledger = store.read_ledger_strict(self.shop, self.root)
            entry = ledger["customers"].get(cid)
            if entry is None:
                raise KeyError(cid)
            entry["balance"] = int(entry["balance"]) + int(amount)
            entry["last_purchase"] = now.date().isoformat()
            entry.setdefault("entries", []).append({"time": now.isoformat(), "call_id": call_id,
                                                    "delta": int(amount), "note": note})
            store.write_ledger(self.shop, ledger, self.root)
            return entry["balance"]
