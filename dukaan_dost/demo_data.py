"""
demo_data.py

Writes clearly synthetic orders, loan enquiries, call records and a credit book for one shop, so a
dashboard has something to show before the agent writes real ones:

    python -m dukaan_dost.demo_data dukaan_dost            # add the demo data
    python -m dukaan_dost.demo_data dukaan_dost --reset    # wipe that shop's orders first

Everything is made up (names, prices, balances) and marked "synthetic": true.
Times are relative to now, so "today" is always populated.
"""

import shutil
import sys
from datetime import datetime, timedelta

from . import store
from .loan_calculator import quote
from .shops import valid_name


def _items(*rows):
    return [{"sku": sku, "name": name, "qty": qty, "unit": unit, "unit_price": price, "line_total": qty * price}
            for sku, name, qty, unit, price in rows]


def build(now: datetime):
    """(orders, loans, ledger) as dicts, with consistent arithmetic."""
    def at(days=0, hours=0, minutes=0):
        return (now - timedelta(days=days, hours=hours, minutes=minutes)).isoformat()

    def order(call_id, when, customer, items, payment, status="confirmed", language="hi-IN",
              before=None, delivery="home delivery"):
        total = sum(i["line_total"] for i in items)
        after = before + total if payment == "udhaar" and before is not None else None
        return {"call_id": call_id, "time": when, "language": language, "status": status,
                "customer": customer, "items": items, "total": total, "payment": payment,
                "delivery": delivery, "balance_before": before, "balance_after": after, "synthetic": True}

    orders = [
        order("d01", at(minutes=4), "Ramesh",
              _items(("RICE-1KG", "Rice", 2, "kg", 60), ("OIL-1L", "Sunflower oil", 1, "litre", 165)),
              "udhaar", before=400),
        order("d02", at(minutes=38), None,
              _items(("MAGGI-70", "Maggi noodles", 4, "pack", 14), ("MILK-500", "Milk", 2, "packet", 30)),
              "upi", language="en-IN", delivery="pickup"),
        order("d03", at(hours=2, minutes=10), "Lakshmi",
              _items(("DAL-TOOR-1KG", "Toor dal", 1, "kg", 145), ("SUGAR-1KG", "Sugar", 2, "kg", 44),
                     ("TEA-250", "Tea", 1, "pack", 120)),
              "udhaar", language="te-IN", before=900),
        order("d04", at(hours=3, minutes=40), "Anita",
              _items(("ATTA-5KG", "Atta (5 kg)", 1, "bag", 260),), "udhaar", status="credit_pending",
              before=1900),
        order("d05", at(hours=5), None, _items(("SOAP-100", "Soap", 3, "bar", 38),), "cash"),
        order("d06", at(hours=6, minutes=30), "Suresh",
              _items(("RICE-1KG", "Rice", 5, "kg", 60),), "cash", status="incomplete", language="hi-IN"),
        order("d07", at(days=1, hours=2), "Venkat",
              _items(("OIL-1L", "Sunflower oil", 2, "litre", 165), ("SALT-1KG", "Salt", 1, "kg", 22)),
              "udhaar", language="te-IN", before=0),
        order("d08", at(days=1, hours=4), None, _items(("BREAD-400", "Bread", 2, "loaf", 45),), "upi"),
    ]
    for n, (days, rows, pay) in enumerate([                 # earlier days, so the sales trend has something to show
        (2, [("RICE-1KG", "Rice", 3, "kg", 60), ("DAL-TOOR-1KG", "Toor dal", 1, "kg", 145)], "cash"),
        (2, [("MILK-500", "Milk", 4, "packet", 30)], "upi"),
        (3, [("ATTA-5KG", "Atta (5 kg)", 2, "bag", 260), ("OIL-1L", "Sunflower oil", 1, "litre", 165)], "upi"),
        (4, [("SUGAR-1KG", "Sugar", 3, "kg", 44), ("TEA-250", "Tea", 1, "pack", 120)], "cash"),
        (4, [("MAGGI-70", "Maggi noodles", 6, "pack", 14)], "cash"),
        (5, [("RICE-1KG", "Rice", 4, "kg", 60), ("SALT-1KG", "Salt", 2, "kg", 22)], "upi"),
        (6, [("SOAP-100", "Soap", 5, "bar", 38), ("BREAD-400", "Bread", 3, "loaf", 45)], "cash"),
    ]):
        orders.append(order(f"d{10 + n}", at(days=days, hours=3 + n), None, _items(*rows), pay))
    orders[2]["balance_after"] = 900 + orders[2]["total"]

    loans = []
    for call_id, when, margin, business, place, lang in [
        ("l01", at(hours=1, minutes=15), 100000, "kirana", "Nandyal", "te-IN"),
        ("l02", at(hours=4), 10000, "tea stall", "Kurnool", "hi-IN"),
        ("l03", at(days=1, hours=1), 14000, "dairy", "Adoni", "hi-IN"),
    ]:
        loans.append({"call_id": call_id, "time": when, "language": lang, "business": business,
                      "place": place, "synthetic": True, **quote(margin).to_dict()})

    def customer(name, balance, limit, last, promise=None):
        return {"name": name, "balance": balance, "credit_limit": limit, "last_purchase": last,
                "promise_date": promise, "entries": []}

    today = now.date()
    ledger = {"customers": {
        "ramesh": customer("Ramesh", 685, 2000, today.isoformat()),
        "lakshmi": customer("Lakshmi", 900 + orders[2]["total"], 2000, today.isoformat(),
                            (today + timedelta(days=3)).isoformat()),
        "anita": customer("Anita", 1900, 2000, today.isoformat()),
        "venkat": customer("Venkat", 380, 1000, (today - timedelta(days=1)).isoformat()),
        "suresh": customer("Suresh", 0, 1500, (today - timedelta(days=9)).isoformat()),
    }}
    return orders, loans, ledger


def build_calls(now: datetime, orders: list, loans: list) -> list:
    """One counts-only call record (the shape call_stats.finish() returns) for each demo order and loan enquiry of the
    last 12 hours, and three calls where nothing came of it, so every state of the dashboard's Calls view has an example."""
    def call(call_id, when, channel, seconds, language, turns, outcome, barge_ins=0, no_speech=0, model_failures=0,
             order=None):
        record = {"call_id": call_id, "time": when, "channel": channel, "seconds": seconds, "language": language,
                  "turns": turns, "barge_ins": barge_ins, "no_speech": no_speech, "model_failures": model_failures,
                  "outcome": outcome, "synthetic": True}
        if order:
            record.update(order_id=order["call_id"], total=order["total"], status=order["status"])
        return record

    recent = now - timedelta(hours=12)           # the last 12 hours, not "today": just after midnight "today" has almost nothing in it
    todays = [o for o in orders if datetime.fromisoformat(o["time"]) >= recent]
    calls = []
    for n, o in enumerate(todays):
        calls.append(call(f"c{n + 1:02d}", o["time"], "phone" if n % 2 else "browser", 70 + 23 * n, o["language"],
                          3 + n % 4, "ordered", barge_ins=1 if n == 2 else 0, no_speech=2 if n == 3 else 0, order=o))
    for n, l in enumerate(l for l in loans if datetime.fromisoformat(l["time"]) >= recent):
        calls.append(call(f"c{20 + n}", l["time"], "browser", 150 + 40 * n, l["language"], 5, "loan"))
    at = lambda minutes: (now - timedelta(minutes=minutes)).isoformat()
    calls += [
        call("c30", at(52), "phone", 41, "hi-IN", 2, "nothing", model_failures=2),
        call("c31", at(95), "phone", 18, None, 0, "nothing", no_speech=3),
        call("c32", at(150), "browser", 64, "en-IN", 3, "nothing", barge_ins=1),
    ]
    return calls


def seed(shop: str, root=None, reset: bool = False, now: datetime | None = None) -> int:
    if not valid_name(shop):
        raise ValueError(f"{shop!r} is not a valid shop name")
    folder = store.shop_orders_dir(shop, root)
    if reset and folder.is_dir():
        shutil.rmtree(folder)
    now = now or datetime.now(store.IST)
    orders, loans, ledger = build(now)
    calls = build_calls(now, orders, loans)
    for o in orders:
        store.write_order(shop, o, root)
    for l in loans:
        store.write_loan(shop, l, root)
    for c in calls:
        store.write_call(shop, c, root)
    store.write_ledger(shop, ledger, root)
    return len(orders) + len(loans) + len(calls)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        raise SystemExit("usage: python -m dukaan_dost.demo_data <shop> [--reset]")
    n = seed(args[0], reset="--reset" in sys.argv)
    print(f"Wrote {n} synthetic records for {args[0]} in {store.shop_orders_dir(args[0])}")
