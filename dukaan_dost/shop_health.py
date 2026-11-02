"""
shop_health.py

What is wrong with a shop, found by looking at its files (the admin dashboard, DEC-034). It runs the
same checks an operator would do by hand before a shop takes a call: can its config be read, has it a
system prompt, is its knowledge in place, is there a stock list, can its shopkeeper sign in.

Each problem is a plain dict, safe to send to a page:

    {"id": "alpha:no-pin", "shop": "alpha", "severity": "warning" | "error",
     "title": "No PIN set", "detail": "The shopkeeper cannot open the dashboard until one is set."}

  - "error":   the agent cannot serve this shop properly (a config it cannot read, no system prompt,
               no always-on knowledge, an unreadable stock list).
  - "warning": the shop works, but something is missing or will be a surprise (a topic file missing,
               no stock list, no PIN, files of orders that could not be read).

The id is stable (shop and code, plus a file name where there are several), so a later "mark solved"
can refer to a problem without guessing.

Nothing here writes anything, and nothing reads outside the shop's own folder: shop names are checked
by shops.valid_name before they become a path.
"""

import json
from pathlib import Path

import yaml

from . import auth, shops, store
from .knowledge_retriever import CORE_FILENAME, KNOWLEDGE_FILES

ERROR = "error"
WARNING = "warning"
SEVERITY_ORDER = {ERROR: 0, WARNING: 1}


def _problem(shop: str, code: str, severity: str, title: str, detail: str) -> dict:
    return {"id": f"{shop}:{code}", "shop": shop, "severity": severity, "title": title, "detail": detail}


def _config_problems(shop: str, folder: Path) -> list:
    path = folder / "config.yaml"
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return [_problem(shop, "config-unreadable", ERROR, "config.yaml cannot be read",
                         "The file is missing or is not valid YAML, so the agent cannot load this shop.")]
    if not isinstance(config, dict):
        return [_problem(shop, "config-unreadable", ERROR, "config.yaml cannot be read",
                         "The file is not a set of settings, so the agent cannot load this shop.")]
    out = []
    prompt = config.get("system_prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        out.append(_problem(shop, "no-prompt", ERROR, "No system prompt",
                            "config.yaml has no system_prompt, so the agent has no instructions for this shop."))
    fallbacks = config.get("fallback_messages")
    if not isinstance(fallbacks, dict) or "en-in" not in {str(k).lower() for k in fallbacks}:
        out.append(_problem(shop, "no-fallback", ERROR, "No English fallback message",
                            "config.yaml needs fallback_messages with an en-in entry, which the agent says when it cannot answer."))
    return out


def _knowledge_problems(shop: str, folder: Path) -> list:
    out = []
    if not (folder / "knowledge" / CORE_FILENAME).is_file():
        out.append(_problem(shop, "no-always-on", ERROR, "Always-on knowledge is missing",
                            f"knowledge/{CORE_FILENAME} is sent on every turn (who the shop is, how to speak); without it the agent has no identity."))
    for name in KNOWLEDGE_FILES:
        if not (folder / "knowledge" / name).is_file():
            out.append(_problem(shop, f"missing-{name}", WARNING, f"Knowledge file missing: {name}",
                                "The agent cannot answer questions that belong in this file."))
    return out


def _stock_problems(shop: str, folder: Path) -> list:
    path = folder / "stock.json"
    if not path.is_file():
        return [_problem(shop, "no-stock", WARNING, "No stock list",
                         "Without stock.json an order cannot be checked against what the shop sells.")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [_problem(shop, "stock-unreadable", ERROR, "stock.json cannot be read",
                         "The stock list is not valid JSON, so orders cannot be checked.")]
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return [_problem(shop, "stock-empty", WARNING, "The stock list is empty", "stock.json has no items.")]
    return []


def check(shop: str, shops_root: Path | None = None, orders_root: Path | None = None,
          auth_path: Path | None = None) -> list:
    """Every problem with this shop, errors first."""
    if not shops.valid_name(shop):
        return []
    folder = shops.shop_dir(shop, shops_root)
    out = []
    out += _config_problems(shop, folder)
    out += _knowledge_problems(shop, folder)
    out += _stock_problems(shop, folder)
    if not auth.has_pin(shop, auth_path):
        out.append(_problem(shop, "no-pin", WARNING, "No PIN set",
                            "The shopkeeper cannot open this shop's dashboard until one is set."))
    try:
        unreadable = store.snapshot(shop, root=orders_root, limit=1)["problems"]
    except Exception:
        unreadable = []
    if unreadable:
        n = len(unreadable)
        out.append(_problem(shop, "unreadable-data", WARNING,
                            f"{n} order or loan {'file' if n == 1 else 'files'} could not be read",
                            "They are skipped on the dashboard until they are fixed or removed."))
    return sorted(out, key=lambda p: (SEVERITY_ORDER.get(p["severity"], 9), p["id"]))
