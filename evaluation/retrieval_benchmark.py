#!/usr/bin/env python3
"""
Compares ways of finding the products a caller's sentence asks for. No model, no network, no tokens: it runs in
seconds. For every phrase in evaluation/retrieval_cases.py it asks each method for its best items and counts how
many of the items really asked for are among them.

    python evaluation/retrieval_benchmark.py                 # print the table
    python evaluation/retrieval_benchmark.py --save          # also write evaluation/results/retrieval_benchmark.json

Methods:
  keyword   the shop's existing knowledge search (whole words, 1,200 character budget): what the first
            evaluation run used. Its "top k" is however many product sections fit in the budget.
  ngram     product_search.ProductSearch (character pieces), top 3 / 5 / 8
  catalogue sending the whole catalogue (no search): by definition every item is available; listed for scale.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.retrieval_cases import CASES  # noqa: E402
from dukaan_dost import knowledge_retriever, stock  # noqa: E402
from dukaan_dost.product_search import ProductSearch  # noqa: E402

SHOP = ROOT / "shops" / "dukaan_dost"


def keyword_skus(text: str) -> list:
    context = knowledge_retriever.get_relevant_context(SHOP, text)
    return re.findall(r"^SKU (\S+) ", context, re.MULTILINE)


def score(found_by_case: list) -> dict:
    asked = hit = full = 0
    sizes = []
    for case, found in found_by_case:
        exp = case["expected"]
        got = [s for s in exp if s in found]
        asked += len(exp)
        hit += len(got)
        full += len(got) == len(exp)
        sizes.append(len(found))
    return {"item_recall": round(hit / asked, 3), "items_found": hit, "items_asked": asked,
            "phrases_fully_covered": f"{full}/{len(found_by_case)}", "avg_items_returned": round(sum(sizes) / len(sizes), 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    items = stock.load(SHOP)
    search = ProductSearch(items)

    methods = {"keyword (existing search)": lambda t: keyword_skus(t)}
    for k in (3, 5, 8):
        methods[f"ngram top {k}"] = (lambda kk: lambda t: [s for s, _ in search.search(t, kk)])(k)

    out = {"phrases": len(CASES), "items_asked": sum(len(c["expected"]) for c in CASES), "methods": {}, "by_source": {}, "misses": {}}
    for name, fn in methods.items():
        t0 = time.perf_counter()
        results = [(c, fn(c["text"])) for c in CASES]
        ms = (time.perf_counter() - t0) * 1000 / len(CASES)
        out["methods"][name] = {**score(results), "ms_per_phrase": round(ms, 2)}
        for source in ("heard", "variant", "holdout"):
            out["by_source"].setdefault(name, {})[source] = score([r for r in results if r[0]["source"] == source])["item_recall"]
        out["misses"][name] = [{"text": c["text"], "missing": [s for s in c["expected"] if s not in f]}
                               for c, f in results if any(s not in f for s in c["expected"])]

    print(f"{out['phrases']} phrases, {out['items_asked']} items asked for (shop: {SHOP.name}, {len(items)} items)\n")
    print(f"{'method':28} {'item recall':>12} {'phrases fully covered':>22} {'items returned':>15} {'ms/phrase':>10}   heard / variant / holdout")
    for name, m in out["methods"].items():
        s = out["by_source"][name]
        print(f"{name:28} {m['item_recall']:>12.3f} {m['phrases_fully_covered']:>22} {m['avg_items_returned']:>15} {m['ms_per_phrase']:>10}   {s['heard']:.2f} / {s['variant']:.2f} / {s['holdout']:.2f}")
    print("\nWhat 'ngram top 8' still misses:")
    for miss in out["misses"]["ngram top 8"]:
        print(f"  {miss['text']}  ->  {miss['missing']}")
    if args.save:
        dest = ROOT / "evaluation" / "results" / "retrieval_benchmark.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nsaved", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
