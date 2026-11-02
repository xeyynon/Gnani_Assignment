"""
store.py

What the agent writes after a call and what the dashboards read, as plain JSON
files, one folder per shop (DEC-034). The files are the contract between the
agent and the dashboards, so the formats are documented here.

    orders/<shop>/order_<call_id>.json
        {"type": "order", "call_id", "shop", "time" (ISO 8601 with offset), "language",
         "status": "confirmed" | "credit_pending" | "incomplete",
         "customer": str | null,
         "items": [{"sku", "name", "qty", "unit", "unit_price", "line_total"}],
         "total": int rupees, "payment": "cash" | "upi" | "udhaar", "delivery": str,
         "balance_before": int | null, "balance_after": int | null, "synthetic": bool}

    orders/<shop>/loan_<call_id>.json
        {"type": "loan", "call_id", "shop", "time", "language", "business": str, "place": str,
         ... the fields of loan_calculator.LoanQuote.to_dict() ..., "synthetic": bool}

    orders/<shop>/ledger.json
        {"customers": {"<key>": {"name", "balance", "credit_limit", "last_purchase" (ISO date) | null,
                                  "promise_date" (ISO date) | null, "entries": [{"time", "call_id", "delta", "note"}]}}}

Writes are atomic (a temp file, then a rename) so a dashboard never reads half a file.
A file that cannot be read is skipped and reported in `problems`, never fatal.
All data in this project is synthetic.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .shops import PROJECT_ROOT, valid_name

ORDERS_DIR = PROJECT_ROOT / "orders"
IST = timezone(timedelta(hours=5, minutes=30), "IST")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ATTENTION = ("credit_pending", "incomplete")


def shop_orders_dir(shop: str, root: Path | None = None) -> Path:
    if not valid_name(shop):
        raise ValueError(f"{shop!r} is not a valid shop name")
    return (root or ORDERS_DIR) / shop


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _record_path(shop, kind, call_id, root):
    if not ID_RE.match(str(call_id)):
        raise ValueError(f"{call_id!r} is not a valid call id")
    return shop_orders_dir(shop, root) / f"{kind}_{call_id}.json"


def write_order(shop: str, order: dict, root: Path | None = None) -> Path:
    path = _record_path(shop, "order", order["call_id"], root)
    _atomic_write(path, {**order, "type": "order", "shop": shop})
    return path


def write_order_text(shop: str, call_id: str, text: str, root: Path | None = None) -> Path:
    """A readable copy of the order (order_<call_id>.txt) next to the JSON; the dashboards only read the JSON."""
    if not ID_RE.match(str(call_id)):
        raise ValueError(f"{call_id!r} is not a valid call id")
    path = shop_orders_dir(shop, root) / f"order_{call_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return path


def write_loan(shop: str, loan: dict, root: Path | None = None) -> Path:
    path = _record_path(shop, "loan", loan["call_id"], root)
    _atomic_write(path, {**loan, "type": "loan", "shop": shop})
    return path


def read_ledger(shop: str, root: Path | None = None) -> dict:
    try:
        data = json.loads((shop_orders_dir(shop, root) / "ledger.json").read_text(encoding="utf-8"))
        return data if isinstance(data.get("customers"), dict) else {"customers": {}}
    except (OSError, ValueError, AttributeError):
        return {"customers": {}}


def write_ledger(shop: str, ledger: dict, root: Path | None = None) -> None:
    _atomic_write(shop_orders_dir(shop, root) / "ledger.json", ledger)


def _parse_time(value):
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=IST)


def read_records(shop: str, kind: str, root: Path | None = None):
    """(records newest first, names of files that could not be read)."""
    folder = shop_orders_dir(shop, root)
    records, problems = [], []
    if not folder.is_dir():
        return records, problems
    for path in folder.glob(f"{kind}_*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ValueError("not an object")
        except (OSError, ValueError):
            problems.append(path.name)
            continue
        record["_id"] = path.stem.split("_", 1)[1]
        record["_when"] = _parse_time(record.get("time")) or datetime.fromtimestamp(path.stat().st_mtime, IST)
        records.append(record)
    records.sort(key=lambda r: r["_when"], reverse=True)
    return records, sorted(problems)


def _int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _public_order(r: dict) -> dict:
    items = r.get("items") if isinstance(r.get("items"), list) else []
    return {
        "id": r["_id"], "time": r["_when"].isoformat(), "language": r.get("language"),
        "status": r.get("status") or "confirmed", "customer": r.get("customer"),
        "items": [{"name": str(i.get("name", "?")), "qty": i.get("qty"), "unit": i.get("unit"),
                   "line_total": _int(i.get("line_total"))} for i in items if isinstance(i, dict)],
        "total": _int(r.get("total")), "payment": r.get("payment"), "delivery": r.get("delivery"),
        "balance_before": r.get("balance_before"), "balance_after": r.get("balance_after"),
        "synthetic": bool(r.get("synthetic")),
    }


def _public_loan(r: dict) -> dict:
    keys = ("margin_money", "project_cost", "covered", "scheme", "annual_rate_pct", "loan_amount",
            "own_contribution", "monthly_instalment", "repayment_months", "moratorium_months",
            "total_interest", "language", "business", "place")
    return {"id": r["_id"], "time": r["_when"].isoformat(), "synthetic": bool(r.get("synthetic")),
            **{k: r.get(k) for k in keys}}


def snapshot(shop: str, now: datetime | None = None, root: Path | None = None, limit: int = 30) -> dict:
    """Everything a dashboard shows, in one JSON-ready dict."""
    now = (now or datetime.now(IST)).astimezone(IST)
    orders, bad_orders = read_records(shop, "order", root)
    loans, bad_loans = read_records(shop, "loan", root)
    ledger = read_ledger(shop, root)["customers"]

    today = now.date()
    todays = [o for o in orders if o["_when"].astimezone(IST).date() == today]
    customers = []
    for key, c in ledger.items():
        if not isinstance(c, dict):
            continue
        customers.append({"key": key, "name": c.get("name") or key, "balance": _int(c.get("balance")),
                          "credit_limit": _int(c.get("credit_limit")), "last_purchase": c.get("last_purchase"),
                          "promise_date": c.get("promise_date")})
    customers.sort(key=lambda c: (-c["balance"], c["name"]))
    owing = [c for c in customers if c["balance"] > 0]

    def day_sales(day):
        return sum(_int(o.get("total")) for o in orders
                   if o["_when"].astimezone(IST).date() == day and o.get("status") != "incomplete")

    def day_orders(day):
        return sum(1 for o in orders if o["_when"].astimezone(IST).date() == day)

    yesterday = today - timedelta(days=1)
    # Yesterday only up to this time of day, so "vs yesterday" compares like with like: at 10 am today is not
    # measured against a whole day of sales.
    same_time = now - timedelta(days=1)
    yesterday_so_far = [o for o in orders if o["_when"].astimezone(IST).date() == yesterday
                        and o["_when"].astimezone(IST) <= same_time]
    trend = [{"date": (today - timedelta(days=n)).isoformat(), "sales": day_sales(today - timedelta(days=n)),
              "orders": day_orders(today - timedelta(days=n))} for n in range(6, -1, -1)]

    return {
        "shop": shop,
        "generated_at": now.isoformat(),
        "summary": {
            "orders_today": len(todays),
            "sales_today": sum(_int(o.get("total")) for o in todays if o.get("status") != "incomplete"),
            "orders_total": len(orders),
            "orders_yesterday": day_orders(yesterday),
            "sales_yesterday": day_sales(yesterday),
            "orders_yesterday_same_time": len(yesterday_so_far),
            "sales_yesterday_same_time": sum(_int(o.get("total")) for o in yesterday_so_far
                                             if o.get("status") != "incomplete"),
            "udhaar_outstanding": sum(c["balance"] for c in owing),
            "customers_owing": len(owing),
            "loans_today": sum(1 for l in loans if l["_when"].astimezone(IST).date() == today),
            "loans_total": len(loans),
            "needs_attention": sum(1 for o in orders if o.get("status") in ATTENTION),
        },
        "trend": trend,
        "orders": [_public_order(o) for o in orders[:limit]],
        "loans": [_public_loan(l) for l in loans[:limit]],
        "ledger": customers,
        "problems": [f"{n}: could not be read" for n in bad_orders + bad_loans],
    }
