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
  time to first audio   from the caller's LAST WORD to the first sample of the agent's reply: the time from the end of the
                   audio file plus the quiet at the end of that file (20 ms frames with RMS under 300; the Timbre clips end with
                   a pause). The figure from the end of the file is shown beside it, labelled. A turn whose clip is missing
                   and has no recorded silence is left uncorrected, and the output says how many
  loan calls       scored on the saved loan quote and reported on their own row; they are left out of the order figures
                   (exact, recall, precision, payment)
  valid run        false when the run did not finish every scripted call, when the model refused requests (Groq 429 or Gemini
                   RESOURCE_EXHAUSTED/quota; each refused request counted once), or when there is no <run>.agent.log to check
                   (pass --no-log-ok to accept that)
  WER              the speech recogniser's text against the words spoken, raw and "number-normalised"
                   (spoken numbers and digits compared as the same thing; punctuation and case ignored)
All speech is synthetic Timbre speech, so results are optimistic compared with real callers.
T-WER            of the Latin-script (English) words in what was spoken, the share the recogniser missed; a word counts as
                   right if it came back in Latin letters or as a Hindi or Telugu word that identifies the same product (the
                   recogniser may write "Maggi" as मैगी). Only words that belong to exactly one stock item's names count, and
                   only for an English word that itself belongs to one item, never a generic word (का, तेल, जी) or a word
                   shared by several products, so "oil" or "biscuits" must come back in Latin letters. Other English words
                   need the Latin form too.
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


STOPWORDS = {"का", "की", "के", "में", "से", "जी", "डे", "और", "है", "को", "ने", "గా", "లో", "కి", "ల", "ను"}


def english_variants(items) -> dict:
    """Latin word -> the Hindi and Telugu words that identify the same product, from the shop's stock list. A Hindi or Telugu
    word is kept only if it is in the names of exactly one item and is not a stopword, and a Latin word gets variants only
    if it too belongs to exactly one item; so generic words (का, तेल) and the words of other products never count."""
    items = list(items)
    other_words = []                                   # per item: its Hindi and Telugu name words
    latin_words = []                                   # per item: its Latin name and alias words
    for it in items:
        names = it["name"]
        other_words.append({w for lang in ("hi", "te") for w in words(names.get(lang, ""))})
        latin_words.append({w for w in words(re.sub(r"\s*\(.*?\)", "", names["en"]) + " " + " ".join(it.get("aliases", [])))
                            if w.isascii() and w.isalpha()})
    owners_other, owners_latin = {}, {}
    for k in range(len(items)):
        for w in other_words[k]:
            owners_other.setdefault(w, set()).add(k)
        for w in latin_words[k]:
            owners_latin.setdefault(w, set()).add(k)
    out = {}
    for w, owners in owners_latin.items():
        if len(owners) != 1:
            continue
        k = next(iter(owners))
        keep = {o for o in other_words[k] if len(owners_other[o]) == 1 and o not in STOPWORDS}
        if keep:
            out[w] = keep
    return out


def t_wer(ref: list, hyp: list, variants: dict) -> tuple:
    """(English words missed, English words spoken). Each Latin word in the reference is right if the recogniser wrote it in
    Latin letters or wrote a Hindi or Telugu word that identifies the same product (see english_variants)."""
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


LEAD_IN_SEC = 2          # a record may be stamped a little before the call's recorded begin (clock skew)


def _ts(iso):
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return None


def assign_records(call_recs: list, records: list) -> list:
    """For each call (the result is in the same order), the record it saved or None. A record belongs to the call whose window
    [begin - 2 s, end] holds its time; each record goes to one call only, the pairs nearest to a call's begin first. The window
    ends at the call's end, never later: the next call begins at that moment, so its record must not be taken by this call."""
    stamped = [(t, r) for r in records for t in [_ts(r.get("time"))] if t is not None]
    pairs = []
    for ci, c in enumerate(call_recs):
        b, e = _ts(c.get("begin_iso")), _ts(c.get("end_iso"))
        if b is None or e is None:
            continue
        for ri, (t, _) in enumerate(stamped):
            if b - LEAD_IN_SEC <= t <= e:
                pairs.append((abs(t - b), ci, ri))
    out, used = [None] * len(call_recs), set()
    for _, ci, ri in sorted(pairs):
        if out[ci] is None and ri not in used:
            out[ci] = stamped[ri][1]
            used.add(ri)
    return out


def order_for(call_rec: dict, orders: list):
    """The order saved in this call (see assign_records)."""
    return assign_records([call_rec], orders)[0]


def score_loan(rec, meta, exp, loan) -> dict:
    """A loan call is right when the saved quote has the project cost, loan and instalment the calculator gives."""
    got = loan or {}
    right = {k: got.get(k) == v for k, v in exp.items()}
    return {"id": rec["id"], "lang": meta.get("lang", "?"), "tags": meta.get("tags", []), "order_saved": loan is not None,
            "exact": bool(loan) and all(right.values()), "kind": "loan", "recall": None, "precision": None,
            "extra_items": [], "missing_items": [], "wrong_quantities": {}, "payment_right": None, "payment_got": None,
            "total_matches_stock_list": None, "customer_expected": None, "customer_got": None,
            "order_total": None, "status": None, "loan_expected": exp,
            "loan_got": {k: got.get(k) for k in exp}, "loan_right": right}


def line_total(price, qty) -> int:
    return int((Decimal(str(price)) * Decimal(str(qty))).quantize(Decimal(1), ROUND_HALF_UP))


_STAMP = re.compile(r"^(\d\d:\d\d:\d\d)\b")
_FAILURE = re.compile(r"429 Too Many Requests|RESOURCE_EXHAUSTED|\bquota\b", re.IGNORECASE)


def refused_requests(log_text: str) -> int:
    """How many model requests were refused, from the agent log. Groq's 429 and Gemini's 429 / RESOURCE_EXHAUSTED / quota
    failures all count. A refused request leaves several lines (httpx's 'HTTP Request ... 429', then the provider's own
    'attempt 1/2 failed' error), so the HTTP request lines are counted one each and any other failure line only if no HTTP
    429 line carries the same time-stamp second; other lines in one second count once. Lines with no time-stamp count each."""
    http, http_seconds, other_seconds, unstamped = 0, set(), set(), 0
    for line in log_text.splitlines():
        m = _STAMP.match(line)
        sec = m.group(1) if m else None
        if "HTTP Request:" in line:
            if re.search(r"\b429\b", line):
                http += 1
                if sec:
                    http_seconds.add(sec)
            continue
        if _FAILURE.search(line) and "[INFO]" not in line:
            if sec:
                other_seconds.add(sec)
            else:
                unstamped += 1
    return http + len(other_seconds - http_seconds) + unstamped


def trailing_silence(turn: dict, cache: dict):
    """(ms of quiet at the end of the turn's clip, where it came from) or (None, why not). New runs record it per turn;
    older ones are measured from the clip named in the turn."""
    if turn.get("trailing_silence_ms") is not None:
        return turn["trailing_silence_ms"], "recorded"
    path = turn.get("audio")
    if not path:
        return None, "no audio path in the result"
    if path not in cache:
        try:
            from dukaan_dost.transport_replay import _wav_pcm, trailing_silence_ms
            cache[path] = (trailing_silence_ms(_wav_pcm(path)), "measured from the clip")
        except Exception:
            cache[path] = (None, "clip missing or unreadable")
    return cache[path]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-log-ok", action="store_true", help="accept a run that has no <run>.agent.log to check for refused requests")
    args = ap.parse_args()

    from dukaan_dost import stock
    run = json.loads(Path(args.run).read_text(encoding="utf-8"))
    script = json.loads((ROOT / "evaluation" / "scripts" / run["script"]).read_text(encoding="utf-8"))
    meta = {c["id"]: c for c in script["calls"]}
    items = {i["sku"]: i for i in stock.load(ROOT / "shops" / "dukaan_dost")}
    orders = load_orders(Path(run["orders_dir"]), "dukaan_dost")
    loans = load_loans(Path(run["orders_dir"]), "dukaan_dost")
    raw = run.get("run") or {}
    run_calls = raw.get("calls", [])

    # did the run finish? the raw result's done flag, and a result for every call that was scripted
    expected_ids = list(run["expected"]) if isinstance(run.get("expected"), dict) else list(meta)
    finished_ids = [c["id"] for c in run_calls]
    missing_calls = [i for i in expected_ids if i not in finished_ids]
    done_flag = raw.get("done") is True
    complete = done_flag and not missing_calls and run.get("complete", True) is not False and not raw.get("aborted")

    log_path = Path(args.run).with_suffix(".agent.log")
    log_found = log_path.exists()
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_found else ""
    rate_limited = refused_requests(log_text)                       # the model refused a request: those turns are not accuracy results
    log_ok = log_found or args.no_log_ok
    valid_run = bool(complete and rate_limited == 0 and log_ok)

    # orders and loan quotes are given to calls in time order, each record to one call only
    order_calls = [r for r in run_calls if meta[r["id"]].get("kind") != "loan"]
    loan_calls = [r for r in run_calls if meta[r["id"]].get("kind") == "loan"]
    order_of = dict(zip(map(id, order_calls), assign_records(order_calls, orders)))
    loan_of = dict(zip(map(id, loan_calls), assign_records(loan_calls, loans)))

    rows, latencies, latencies_word = [], [], []
    uncorrected_turns, silence_cache, silence_reasons = 0, {}, set()
    raw_err = raw_len = norm_err = norm_len = no_response = turns_total = 0
    variants = english_variants(items.values())
    tw_err = tw_len = split_turns = short_turns = heard_turns = self_cut = 0

    def note_latency(t):
        nonlocal no_response, uncorrected_turns
        if t.get("first_audio_after_ms") is None:
            no_response += 1
            return
        ms = t["first_audio_after_ms"]
        latencies.append(ms)
        quiet, why = trailing_silence(t, silence_cache)
        if quiet is None:
            uncorrected_turns += 1
            silence_reasons.add(why)
        latencies_word.append(ms + (quiet or 0))

    for rec in run_calls:
        cid = rec["id"]
        exp = meta[cid]["expected"]
        if meta[cid].get("kind") == "loan":
            rows.append(score_loan(rec, meta[cid], exp, loan_of[id(rec)]))
            for t in rec["turns"]:
                turns_total += 1
                note_latency(t)
            continue
        order = order_of[id(rec)]
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
            note_latency(t)
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
            "id": cid, "kind": "order", "lang": meta[cid].get("lang", meta[cid].get("tts_lang", "?")), "tags": meta[cid].get("tags", []), "order_saved": order is not None,
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

    order_rows = [r for r in rows if r.get("kind") != "loan"]
    loan_rows = [r for r in rows if r.get("kind") == "loan"]
    by_lang = {l: agg([r for r in order_rows if r["lang"] == l]) for l in sorted({r["lang"] for r in order_rows})}
    by_tag = {t: agg([r for r in order_rows if t in r["tags"]]) for t in sorted({t for r in order_rows for t in r["tags"]})}
    checked = [r["total_matches_stock_list"] for r in rows if r["total_matches_stock_list"] is not None]
    lk = sum(r["exact"] for r in loan_rows)
    loans_summary = {"calls": len(loan_rows), "exact": lk, "exact_rate": round(lk / len(loan_rows), 3) if loan_rows else None,
                     "exact_ci95": wilson(lk, len(loan_rows)), "quotes_saved": sum(r["order_saved"] for r in loan_rows)}

    def ttfa_of(vals):
        return {"n": len(vals), "median": pct(vals, 0.5), "p90": pct(vals, 0.9), "min": min(vals, default=None), "max": max(vals, default=None)}

    ttfa = ttfa_of(latencies_word)                                  # from the caller's last word
    ttfa_file = ttfa_of(latencies)                                  # from the end of the audio file (too small by the clip's trailing silence)
    ttfa["basis"] = "from the caller's last word: first_audio_after_ms plus the quiet at the end of the clip"
    ttfa["turns_without_silence_correction"] = uncorrected_turns
    ttfa_file["basis"] = "from the end of the audio file, uncorrected"
    summary = {
        "source_run": Path(args.run).name, "script": run["script"], "noise_snr_db": run["noise_snr_db"],
        "snr_definition": run.get("snr_definition"),
        "elapsed_sec": run["elapsed_sec"], "model": run["model"], "llm_provider": run.get("llm_provider"), "speech": "synthetic (Timbre)",
        "overall": agg(order_rows), "loans": loans_summary, "by_language": by_lang, "by_tag": by_tag,
        "total_matches_stock_list": f"{sum(checked)}/{len(checked)}", "turns": turns_total,
        "turns_without_response": no_response, "time_to_first_audio_ms": ttfa, "time_to_first_audio_from_clip_end_ms": ttfa_file,
        "wer_raw": round(raw_err / raw_len, 3) if raw_len else None,
        "wer_number_normalised": round(norm_err / norm_len, 3) if norm_len else None,
        "t_wer": round(tw_err / tw_len, 3) if tw_len else None, "english_words": tw_len,
        "cut_off": {"turns_heard": heard_turns, "split_into_pieces": split_turns, "under_half_the_words": short_turns,
                    "agent_clips_cut_by_the_caller_unscripted": self_cut},
        "rate_limited_requests": rate_limited, "agent_log_found": log_found, "complete": complete,
        "calls_finished": len(run_calls), "calls_expected": len(expected_ids), "calls_missing": missing_calls, "run_done_flag": done_flag,
        "valid_run": valid_run, "reference_words": raw_len, "calls_detail": rows, "not_computed": [],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    o = summary["overall"]
    if run["noise_snr_db"] is None:
        title = f"{Path(args.run).stem}: clean"
    elif run.get("snr_definition"):
        title = f"{Path(args.run).stem}: noise at {run['noise_snr_db']} dB SNR relative to whole-clip RMS of the speech clips"
    else:
        title = (f"{Path(args.run).stem}: noise at {run['noise_snr_db']} dB requested (older run: SNR relative to the RMS of the speech "
                 "samples above 300, not the whole-clip RMS, so the noise was louder than that figure says)")
    provider = f" ({summary['llm_provider']})" if summary.get("llm_provider") not in (None, "unknown") else ""

    def rate(k, n, ci):
        if not n:
            return "no calls"
        return f"{k}/{n} ({k / n:.0%}; 95% interval {ci[0]:.0%} to {ci[1]:.0%})"

    if uncorrected_turns:
        corr_note = (f" ({uncorrected_turns} of {ttfa['n']} turns could not be corrected for trailing silence: "
                     f"{'; '.join(sorted(silence_reasons))}; they are counted from the end of the file)")
    else:
        corr_note = ""
    what = f"{o['calls']} scripted order calls" + (f" and {loans_summary['calls']} loan calls" if loans_summary["calls"] else "")
    missing_text = f" (missing: {', '.join(missing_calls)})" if missing_calls else ""
    never_done = "" if done_flag else " and the run never reached its done flag"
    lines = [f"# {title}", "",
             f"Model: {summary['model']}{provider}. Synthetic Timbre speech; {what}, {turns_total} turns.", "",
             *([f"**INCOMPLETE RUN: {len(run_calls)} of {len(expected_ids)} scripted calls finished{never_done}{missing_text}. "
                "Do not quote these figures.**", ""] if not complete else []),
             *([f"**INVALID RUN: the language model refused {rate_limited} requests (rate limit or quota). Do not quote these figures.**", ""] if rate_limited else []),
             *([f"**CANNOT VERIFY: there is no {log_path.name} to check for refused model requests, so this run is not marked valid.**", ""]
               if not log_found and not args.no_log_ok else []),
             "| Measure | Result |", "|---|---|",
             f"| Orders exactly right (items and quantities; loan calls not included) | {rate(o['exact_orders'], o['calls'], o['exact_ci95'])} |",
             (f"| Item recall / precision (orders only) | {o['item_recall']:.2f} / {o['item_precision']:.2f} |" if o["calls"]
              else "| Item recall / precision (orders only) | no order calls |"),
             f"| Payment chosen correctly (orders only) | {o['payment_right']}/{o['calls']} |",
             *([f"| Loan calls: exact | {rate(lk, len(loan_rows), loans_summary['exact_ci95'])} |"] if loan_rows else []),
             f"| Totals equal to the stock-list arithmetic | {summary['total_matches_stock_list']} |",
             f"| Time to first audio from the caller's last word, median / 90th percentile | {ttfa['median']} ms / {ttfa['p90']} ms (n={ttfa['n']}){corr_note} |",
             f"| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | {ttfa_file['median']} ms / {ttfa_file['p90']} ms (n={ttfa_file['n']}) |",
             f"| Turns with no reply | {no_response}/{turns_total} |",
             f"| Word error rate, raw / number-normalised | {summary['wer_raw']} / {summary['wer_number_normalised']} ({raw_len} words) |",
             f"| T-WER (English words missed) | {summary['t_wer']} ({tw_len} English words) |",
             f"| Cut-off: turns split into pieces / under half the words heard | {split_turns}/{heard_turns} / {short_turns}/{heard_turns} |",
             f"| Agent clips the caller cut short with no interruption scripted | {self_cut} |",
             "", "| Language | Calls | Exact | Recall | Precision |", "|---|---|---|---|---|"]
    for l, a in by_lang.items():
        lines.append(f"| {l} | {a['calls']} | {a['exact_orders']} ({a['exact_rate']:.0%}) | {a['item_recall']:.2f} | {a['item_precision']:.2f} |")
    lines += ["", "| Kind of call (order calls) | Calls | Exact |", "|---|---|---|"]
    for t, a in by_tag.items():
        lines.append(f"| {t} | {a['calls']} | {a['exact_orders']} ({a['exact_rate']:.0%}) |")
    lines += ["", "Calls not exactly right:", ""]
    for r in rows:
        if r["exact"]:
            continue
        if r.get("kind") == "loan":
            lines.append(f"- {r['id']} (loan): got {r['loan_got']}, expected {r['loan_expected']}" + ("" if r["order_saved"] else " (no quote saved)"))
            continue
        extra = [f for f, ok in (("status wrong", r["status_right"]), ("balance wrong", r["balance_right"]),
                                 ("expected phrase not said", r["said_right"])) if not ok]
        lines.append(f"- {r['id']}: missing {r['missing_items']}, extra {r['extra_items']}, wrong quantities "
                     f"{r['wrong_quantities']}" + ("" if r["order_saved"] else " (no order saved)") + (f" ({', '.join(extra)})" if extra else ""))
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
