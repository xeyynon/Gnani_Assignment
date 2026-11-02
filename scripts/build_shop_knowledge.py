#!/usr/bin/env python3
"""
Writes a shop's knowledge/products_pricing.md from its stock.json.

    python scripts/build_shop_knowledge.py shops/dukaan_dost
    python scripts/build_shop_knowledge.py shops/dukaan_dost --check     # exit 1 if the file is stale
    python scripts/build_shop_knowledge.py shops/dukaan_dost --keyterms  # print the Prisma boost list
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import stock  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shop_dir")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--keyterms", action="store_true")
    args = ap.parse_args()

    shop = Path(args.shop_dir)
    try:
        items = stock.load(shop)
    except (ValueError, OSError, KeyError) as e:
        print(e, file=sys.stderr)
        return 1

    if args.keyterms:
        print(",".join(stock.keyterms(items)))
        return 0

    target = shop / "knowledge" / "products_pricing.md"
    wanted = stock.render_products_md(items)
    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current.replace("\r\n", "\n") != wanted:
            print(f"{target} is out of date. Run: python scripts/build_shop_knowledge.py {args.shop_dir}",
                  file=sys.stderr)
            return 1
        print(f"{target} is up to date ({len(items)} items).")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(wanted, encoding="utf-8", newline="\n")
    print(f"Wrote {target} ({len(items)} items, {len(stock.keyterms(items))} Prisma key terms).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
