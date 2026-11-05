#!/usr/bin/env python3
"""
Scores a run made by evaluation/run_calls.py and writes the result as JSON plus a Markdown table.

    python evaluation/score_calls.py evaluation/audio/run_clean_1.json --out evaluation/results/orders_clean.json

For every scripted call it finds the order file the agent wrote and compares it to the expected order:
  exact order      the same items and the same quantities, nothing missing, nothing extra
  item recall      expected items that are in the order / expected items
  item precision   items in the order that were expected / items in the order
  payment          the payment chosen matches
  total            the order's total equals the sum of price x quantity from the stock list
  time to first audio   from the end of the caller's speech to the first sample of the agent's reply
  WER              the speech recogniser's text against the words spoken, raw and "number-normalised"
                   (spoken numbers and digits compared as the same thing; punctuation and case ignored)
All speech is synthetic Timbre speech, so results are optimistic compared with real callers.
T-WER            of the Latin-script (English) words in what was spoken, the share the recogniser missed; a word counts as
                   right if it came back in Latin letters or as the Hindi or Telugu name of the same product (the recogniser
                   may write "Maggi" as मैगी). Only product words are known in both scripts, so other English words need the Latin form.
  cut-off          turns where the endpointing split one sentence into several pieces, turns where the heard text has under half
                   of the spoken words, and agent replies the caller's own speech cut short when no interruption was scripted
"""

import argparse
import json
import math
import re
import statistics
import sys
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NUMBER_WORDS = {
    # English and Hinglish spellings
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
    "nine": "9", "ten": "10", "half": "0.5", "kg": "kilo", "kilos": "kilo", "kilogram": "kilo", "liter": "litre",
    "liters": "litre", "litres": "litre", "packets": "packet",
    "ek": "1", "do": "2", "teen": "3", "char": "4", "paanch": "5", "chhe": "6", "saat": "7", "aath": "8", "nau": "9",
    "das": "10", "aadha": "0.5", "adha": "0.5", "dedh": "1.5",
    # Devanagari
    "एक": "1", "दो": "2", "तीन": "3", "चार": "4", "पांच": "5", "पाँच": "5", "छह": "6", "सात": "7", "आठ": "8", "नौ": "9",
    "दस": "10", "आधा": "0.5", "डेढ़": "1.5",
    # Telugu
    "ఒక": "1", "ఒకటి": "1", "రెండు": "2", "మూడు": "3", "నాలుగు": "4", "ఐదు": "5", "ఆరు": "6", "ఏడు": "7", "ఎనిమిది": "8",
    "తొమ్మిది": "9", "పది": "10", "అర": "0.5", "కిలోల": "కిలో", "కిలోలు": "కిలో",
}


def words(text: str, normalise: bool = False) -> list:
    text = (text or "").lower().replace("।", " ").replace("॥", " ")        # the Hindi full stops lie inside the script range
    text = re.sub(r"[^\w\s.ऀ-෿]", " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)
    ws = text.split()
    if normalise:
        ws = [NUMBER_WORDS.get(w, w) for w in ws]
    return ws


def english_variants(items) -> dict:
    """Latin word -> the Hindi and Telugu words that are the same product, from the shop's stock list."""
    out = {}
    for it in items:
        names = it["name"]
        others = {w for lang in ("hi", "te") for w in words(names.get(lang, ""))}
        for w in words(re.sub(r"\s*\(.*?\)", "", names["en"]) + " " + " ".join(it.get("aliases", []))):
            if w.isascii() and w.isalpha():
                out.setdefault(w, set()).update(others)
    return out


def t_wer(ref: list, hyp: list, variants: dict) -> tuple:
    """(English words missed, English words spoken). Each Latin word in the reference is right if the recogniser wrote it in
    Latin letters or wrote the same product in Hindi or Telugu."""
    heard = set(hyp)
    english = [w for w in ref if w.isascii() and w.isalpha()]
    missed = sum(1 for w in english if w not in heard and not (variants.get(w, set()) & heard))
    return missed, len(english)


def wer(ref: list, hyp: list) -> tuple:
    """(edit distance, reference length)."""
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1], len(ref)


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def pct(values, q):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return round(values[lo] + (values[hi] - values[lo]) * (k - lo))


def load_orders(orders_dir: Path, shop: str) -> list:
    out = []
    for f in sorted((orders_dir / shop).glob("order_*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return out


def load_loans(orders_dir: Path, shop: str) -> list:
    out = []
    for f in sorted((orders_dir / shop).glob("loan_*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return out


def order_for(call_rec: dict, orders: list):
    """The order whose start time falls inside this call."""
    lo = datetime.fromisoformat(call_rec["begin_iso"]).timestamp() - 5
    hi = datetime.fromisoformat(call_rec["end_iso"]).timestamp() + 5
    for o in orders:
        try:
            if lo <= datetime.fromisoformat(o["time"]).timestamp() <= hi:
                return o
        except (KeyError, ValueError):
            continue
    return None


def score_loan(rec, meta, exp, loan) -> dict:
    """A loan call is right when the saved quote has the project cost, loan and instalment the calculator gives."""
    got = loan or {}
    right = {k: got.get(k) == v for k, v in exp.items()}
    return {"id": rec["id"], "lang": meta.get("lang", "?"), "tags": meta.get("tags", []), "order_saved": loan is not None,
            "exact": bool(loan) and all(right.values()), "recall": 1.0 if loan else 0.0, "precision": 1.0 if loan else 0.0,
            "extra_items": [], "missing_items": [], "wrong_quantities": {}, "payment_right": True, "payment_got": None,
            "total_matches_stock_list": None, "customer_expected": None, "customer_got": None,
            "order_total": None, "status": None, "loan_expected": exp,
            "loan_got": {k: got.get(k) for k in exp}, "loan_right": right}


def line_total(price, qty) -> int:
    return int((Decimal(str(price)) * Decimal(str(qty))).quantize(Decimal(1), ROUND_HALF_UP))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from dukaan_dost import stock
    run = json.loads(Path(args.run).read_text(encoding="utf-8"))
    script = json.loads((ROOT / "evaluation" / "scripts" / run["script"]).read_text(encoding="utf-8"))
    meta = {c["id"]: c for c in script["calls"]}
    items = {i["sku"]: i for i in stock.load(ROOT / "shops" / "dukaan_dost")}
    orders = load_orders(Path(run["orders_dir"]), "dukaan_dost")
    loans = load_loans(Path(run["orders_dir"]), "dukaan_dost")

    log_path = Path(args.run).with_suffix(".agent.log")
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    rate_limited = log_text.count("429 Too Many Requests")          # the model refused a request: those turns are not accuracy results
    rows, latencies = [], []
    raw_err = raw_len = norm_err = norm_len = no_response = turns_total = 0
    variants = english_variants(items.values())
    tw_err = tw_len = split_turns = short_turns = heard_turns = self_cut = 0
    for rec in run["run"]["calls"]:
        cid = rec["id"]
        exp = meta[cid]["expected"]
        if meta[cid].get("kind") == "loan":
            rows.append(score_loan(rec, meta[cid], exp, order_for(rec, loans)))
            for t in rec["turns"]:
                turns_total += 1
                if t.get("first_audio_after_ms") is not None:
                    latencies.append(t["first_audio_after_ms"])
                else:
                    no_response += 1
            continue
        order = order_for(rec, orders)
        got = {l["sku"]: float(l["qty"]) for l in order["items"]} if order else {}
        want = {k: float(v) for k, v in exp["items"].items()}
        present = [k for k in want if k in got]
        qty_ok = [k for k in present if abs(got[k] - want[k]) < 1e-9]
        exact = bool(order) and got.keys() == want.keys() and len(qty_ok) == len(want)
        said = [a for tr in rec["turns"] for a in tr.get("agent_said", [])]
        says_ok = all(any(s in a for a in said) for s in exp.get("says", []))
        status_ok = exp.get("status") is None or (order or {}).get("status") == exp["status"]
        balance_ok = "balance_after" not in exp or (order or {}).get("balance_after") == exp["balance_after"]
        if exp.get("no_order"):                                     # e.g. a balance enquiry: nothing should be saved
            exact = order is None
        exact = exact and says_ok and status_ok and balance_ok
        total_ok = None
        if order:
            total_ok = sum(line_total(items[l["sku"]]["price"], l["qty"]) for l in order["items"]) == order["total"]
        for t in rec["turns"]:
            turns_total += 1
            if t.get("first_audio_after_ms") is not None:
                latencies.append(t["first_audio_after_ms"])
            else:
                no_response += 1
            heard = " ".join(t.get("heard") or [])
            e, n = wer(words(t["text"]), words(heard)); raw_err += e; raw_len += n
            e, n = wer(words(t["text"], True), words(heard, True)); norm_err += e; norm_len += n
            e, n = t_wer(words(t["text"]), words(heard), variants); tw_err += e; tw_len += n
            pieces = t.get("heard") or []
            if pieces:
                heard_turns += 1
                split_turns += len(pieces) > 1
                short_turns += len(words(heard)) < 0.5 * len(words(t["text"]))
        if not any(t.get("barge_in_after_sec") is not None for t in meta[cid].get("turns", [])):
            self_cut += rec.get("interrupted_clips", 0)
        rows.append({
            "id": cid, "lang": meta[cid].get("lang", meta[cid].get("tts_lang", "?")), "tags": meta[cid].get("tags", []), "order_saved": order is not None,
            "exact": exact, "recall": (len(present) / len(want)) if want else 1.0,
            "precision": (len([k for k in got if k in want]) / len(got)) if got else (1.0 if not want else 0.0),
            "extra_items": sorted(k for k in got if k not in want), "missing_items": sorted(k for k in want if k not in got),
            "wrong_quantities": {k: [want[k], got[k]] for k in present if k not in qty_ok},
            "payment_right": (order or {}).get("payment") == exp["payment"] or bool(exp.get("no_order") and order is None),
            "payment_got": (order or {}).get("payment"), "status_right": status_ok, "balance_right": balance_ok,
            "said_right": says_ok,
            "total_matches_stock_list": total_ok, "customer_expected": exp.get("customer"),
            "customer_got": (order or {}).get("customer"), "order_total": (order or {}).get("total"),
            "status": (order or {}).get("status"),
        })

    def agg(sub):
        n = len(sub)
        k = sum(r["exact"] for r in sub)
        return {"calls": n, "exact_orders": k, "exact_rate": round(k / n, 3) if n else None, "exact_ci95": wilson(k, n),
                "item_recall": round(statistics.mean(r["recall"] for r in sub), 3) if n else None,
                "item_precision": round(statistics.mean(r["precision"] for r in sub), 3) if n else None,
                "payment_right": sum(r["payment_right"] for r in sub), "orders_saved": sum(r["order_saved"] for r in sub)}

    by_lang = {l: agg([r for r in rows if r["lang"] == l]) for l in sorted({r["lang"] for r in rows})}
    by_tag = {t: agg([r for r in rows if t in r["tags"]]) for t in sorted({t for r in rows for t in r["tags"]})}
    checked = [r["total_matches_stock_list"] for r in rows if r["total_matches_stock_list"] is not None]
    ttfa = {"n": len(latencies), "median": pct(latencies, 0.5), "p90": pct(latencies, 0.9),
            "min": min(latencies, default=None), "max": max(latencies, default=None)}
    summary = {
        "source_run": Path(args.run).name, "script": run["script"], "noise_snr_db": run["noise_snr_db"],
        "elapsed_sec": run["elapsed_sec"], "model": run["model"], "speech": "synthetic (Timbre)",
        "overall": agg(rows), "by_language": by_lang, "by_tag": by_tag,
        "total_matches_stock_list": f"{sum(checked)}/{len(checked)}", "turns": turns_total,
        "turns_without_response": no_response, "time_to_first_audio_ms": ttfa,
        "wer_raw": round(raw_err / raw_len, 3) if raw_len else None,
        "wer_number_normalised": round(norm_err / norm_len, 3) if norm_len else None,
        "t_wer": round(tw_err / tw_len, 3) if tw_len else None, "english_words": tw_len,
        "cut_off": {"turns_heard": heard_turns, "split_into_pieces": split_turns, "under_half_the_words": short_turns,
                    "agent_clips_cut_by_the_caller_unscripted": self_cut},
        "rate_limited_requests": rate_limited, "valid_run": rate_limited == 0, "reference_words": raw_len, "calls_detail": rows, "not_computed": [],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    o = summary["overall"]
    title = f"{Path(args.run).stem}: " + (f"noise at {run['noise_snr_db']} dB SNR" if run["noise_snr_db"] is not None else "clean")
    lines = [f"# {title}", "",
             f"Model: {summary['model']}. Synthetic Timbre speech; {o['calls']} scripted calls, {turns_total} turns.", "",
             *([f"**INVALID RUN: the language model refused {rate_limited} requests (rate limit). Do not quote these figures.**", ""] if rate_limited else []),
             "| Measure | Result |", "|---|---|",
             f"| Orders exactly right (items and quantities) | {o['exact_orders']}/{o['calls']} ({o['exact_rate']:.0%}; 95% interval {o['exact_ci95'][0]:.0%} to {o['exact_ci95'][1]:.0%}) |",
             f"| Item recall / precision | {o['item_recall']:.2f} / {o['item_precision']:.2f} |",
             f"| Payment chosen correctly | {o['payment_right']}/{o['calls']} |",
             f"| Totals equal to the stock-list arithmetic | {summary['total_matches_stock_list']} |",
             f"| Time to first audio, median / 90th percentile | {ttfa['median']} ms / {ttfa['p90']} ms (n={ttfa['n']}) |",
             f"| Turns with no reply | {no_response}/{turns_total} |",
             f"| Word error rate, raw / number-normalised | {summary['wer_raw']} / {summary['wer_number_normalised']} ({raw_len} words) |",
             f"| T-WER (English words missed) | {summary['t_wer']} ({tw_len} English words) |",
             f"| Cut-off: turns split into pieces / under half the words heard | {split_turns}/{heard_turns} / {short_turns}/{heard_turns} |",
             f"| Agent clips the caller cut short with no interruption scripted | {self_cut} |",
             "", "| Language | Calls | Exact | Recall | Precision |", "|---|---|---|---|---|"]
    for l, a in by_lang.items():
        lines.append(f"| {l} | {a['calls']} | {a['exact_orders']} ({a['exact_rate']:.0%}) | {a['item_recall']:.2f} | {a['item_precision']:.2f} |")
    lines += ["", "| Kind of call | Calls | Exact |", "|---|---|---|"]
    for t, a in by_tag.items():
        lines.append(f"| {t} | {a['calls']} | {a['exact_orders']} ({a['exact_rate']:.0%}) |")
    lines += ["", "Calls not exactly right:", ""]
    for r in rows:
        if not r["exact"]:
            lines.append(f"- {r['id']}: missing {r['missing_items']}, extra {r['extra_items']}, wrong quantities "
                         f"{r['wrong_quantities']}" + ("" if r["order_saved"] else " (no order saved)"))
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
