"""
stock.py

A shop's stock list: shops/<name>/stock.json is the one source of truth for what the
shop sells. From it come

  - knowledge/products_pricing.md, the file the language model reads (one `##` section
    per item, with the English, Hindi and Telugu names, so keyword retrieval finds the
    item whichever language the caller names it in), and
  - the product-name boost list for Gnani Prisma (keyterms),

and, when the order flow is built, the list the code checks every spoken item against.
Keeping one source stops the three from drifting apart.

    python scripts/build_shop_knowledge.py shops/dukaan_dost            # write the markdown
    python scripts/build_shop_knowledge.py shops/dukaan_dost --check    # fail if it is out of date
"""

import json
import re
from pathlib import Path

UNITS = {"kg", "litre", "packet", "piece", "bar", "bottle", "bag", "loaf"}
LANGUAGES = ("en", "hi", "te")
SKU = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,30}$")

GENERATED_NOTE = ("<!-- Generated from stock.json by scripts/build_shop_knowledge.py. "
                  "Edit stock.json, then run the script. -->")


def load(shop_dir) -> list:
    """The shop's items, validated. Raises ValueError listing every problem found."""
    path = Path(shop_dir) / "stock.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"]
    problems = validate(items)
    if problems:
        raise ValueError(f"{path} has {len(problems)} problem(s):\n  " + "\n  ".join(problems))
    return items


def validate(items) -> list:
    problems, seen = [], set()
    for i, it in enumerate(items):
        where = it.get("sku", f"item {i}")
        sku = it.get("sku", "")
        if not SKU.match(sku):
            problems.append(f"{where}: sku must be capital letters, digits and hyphens")
        if sku in seen:
            problems.append(f"{where}: duplicate sku")
        seen.add(sku)
        for lang in LANGUAGES:
            if not str(it.get("name", {}).get(lang, "")).strip():
                problems.append(f"{where}: missing {lang} name")
        if it.get("unit") not in UNITS:
            problems.append(f"{where}: unit {it.get('unit')!r} is not one of {sorted(UNITS)}")
        price = it.get("price")
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
            problems.append(f"{where}: price must be a positive number")
        if not isinstance(it.get("in_stock"), bool):
            problems.append(f"{where}: in_stock must be true or false")
        if not it.get("aliases"):
            problems.append(f"{where}: needs at least one alias (how callers say it in Latin letters)")
    return problems


def _money(price) -> str:
    return f"₹{price:g}"


def render_products_md(items) -> str:
    sections = [GENERATED_NOTE]
    for it in items:
        n = it["name"]
        lines = [f"## {n['en']} — {n['hi']} — {n['te']}"]
        status = "in stock" if it["in_stock"] else "OUT OF STOCK today, do not offer it; suggest something similar"
        lines.append(f"SKU {it['sku']} · {it['pack']} · {_money(it['price'])} per {it['unit']} · {status}")
        lines.append("Also called: " + ", ".join(it["aliases"]))
        sections.append("\n".join(lines))
    return "\n\n".join(sections) + "\n"


def keyterms(items, limit: int = 200) -> list:
    """
    Words to boost in Prisma: Latin-script names and aliases (HTTP headers are ASCII). Every
    item's main name comes first, then the aliases, so the cap of 200 cuts aliases and never
    a whole product.
    """
    main = [re.sub(r"\s*\(.*?\)", "", it["name"]["en"]).strip() for it in items]
    aliases = [a for it in items for a in it["aliases"]]
    out, seen = [], set()
    for c in main + aliases:
        c = " ".join(c.split())
        key = c.lower()
        if len(c) < 3 or key in seen or not c.isascii() or "," in c:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= limit:
            break
    return out


def by_sku(items) -> dict:
    return {it["sku"]: it for it in items}
