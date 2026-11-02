"""
admin_actions.py

Everything the admin dashboard can CHANGE (DEC-042), kept apart from the web layer so each action can be tested on
a temporary folder and nothing here knows about sockets. Every function either does its whole job or raises
ValueError with a message that is safe to show the operator; none leaves a half-made shop behind.

    create_shop     a new shop from a blank skeleton or a copy of an existing shop, with its PIN
    set_pin         set or reset a shop's PIN (a generated one is returned once, never stored in clear)
    get_shop        what the editor shows: name, prompt, stock list
    save_prompt     the shop's display name and system prompt
    save_stock      change prices and availability, add and remove items (and rewrite the knowledge file)
    dismiss/restore mark a WARNING solved or bring it back (errors cannot be dismissed: they are real)
    log_event       one line in data/admin_log.jsonl for each change, shown on the admin page's Activity view

Rules:
  - Shop names are validated by shops.valid_name before they become a path; an existing shop is never overwritten.
  - A new shop is built in a hidden folder inside shops/ and renamed into place in one step, so the agent
    (which lists shop folders) never sees a shop that is half written.
  - config.yaml is rewritten from its parsed content, which drops its comments, so the previous file is kept as
    config.yaml.bak first.
  - stock.json is validated as a whole (stock.validate) before it is written, then knowledge/products_pricing.md
    is regenerated from it, because the two must never disagree.
  - Nothing is deleted from disk by any of these actions. Removing a shop is not an admin action.
  - The activity log says WHAT was done and to which shop. It never holds a PIN, a prompt or any text the operator
    typed beyond a short note on a solved problem, so reading it reveals nothing that could be misused.
"""

import json
import os
import secrets
import shutil
import threading
from datetime import datetime
from pathlib import Path

import yaml

from . import auth, shop_health, shops, stock, store
from .knowledge_retriever import CORE_FILENAME, KNOWLEDGE_FILES

STATE_FILE = shops.PROJECT_ROOT / "data" / "admin_state.json"
LOG_FILE = shops.PROJECT_ROOT / "data" / "admin_log.jsonl"
LOG_TAIL_BYTES = 64 * 1024        # how much of the end of the log is read: enough for the latest few hundred lines
MAX_DETAIL_CHARS = 200
_log_lock = threading.Lock()
MAX_PROMPT_CHARS = 20000
MAX_NAME_CHARS = 60
GENERATED_PIN_DIGITS = 6

BLANK_PROMPT = (
    "You are the voice assistant of a neighbourhood shop. Take orders from callers politely and briefly.\n"
    "Only offer items that are in the shop's knowledge. If you do not know something, say the shopkeeper\n"
    "will let them know. Never invent an item, a price or an offer.\n"
)
BLANK_FALLBACK = "Sorry, I did not catch that. Could you please say it again?"
BLANK_ALWAYS_ON = "# About this shop\n\nWrite who the shop is, where it is and how it talks to callers.\n"
BLANK_TOPIC = "<!-- Add this topic's questions and answers as `##` sections. -->\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _check_shop(name, shops_root) -> Path:
    if not shops.valid_name(name):
        raise ValueError("That is not a valid shop name.")
    folder = shops.shop_dir(name, shops_root)
    if not folder.is_dir():
        raise ValueError("There is no such shop.")
    return folder


def _clean_title(title) -> str:
    title = (title or "").strip() if isinstance(title, str) else ""
    if not title:
        raise ValueError("Give the shop a name people will recognise.")
    if len(title) > MAX_NAME_CHARS:
        raise ValueError(f"The shop's name can be at most {MAX_NAME_CHARS} characters.")
    return title


def _pin_or_generate(pin) -> tuple:
    """(pin to set, generated?). A chosen PIN is checked; none given makes a random one."""
    if pin in (None, ""):
        return "".join(secrets.choice("0123456789") for _ in range(GENERATED_PIN_DIGITS)), True
    if not isinstance(pin, str) or len(pin) < auth.MIN_PIN_LENGTH:
        raise ValueError(f"A PIN needs at least {auth.MIN_PIN_LENGTH} characters.")
    return pin, False


# ---------------------------------------------------------------- create

def _write_blank(folder: Path, title: str) -> None:
    config = {"display_name": title, "system_prompt": BLANK_PROMPT, "fallback_messages": {"en-in": BLANK_FALLBACK}}
    _atomic_write(folder / "config.yaml", yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    _atomic_write(folder / "knowledge" / CORE_FILENAME, BLANK_ALWAYS_ON)
    for name in KNOWLEDGE_FILES:
        _atomic_write(folder / "knowledge" / name, BLANK_TOPIC)
    _atomic_write(folder / "stock.json", json.dumps({"currency": "INR", "items": []}, indent=2) + "\n")


def _copy_template(source: Path, folder: Path, title: str) -> None:
    shutil.copytree(source, folder, ignore=shutil.ignore_patterns("*.tmp", "*.bak"))
    config = yaml.safe_load((folder / "config.yaml").read_text(encoding="utf-8")) or {}
    config["display_name"] = title
    _atomic_write(folder / "config.yaml", yaml.safe_dump(config, allow_unicode=True, sort_keys=False))


def create_shop(name, display_name, template="blank", pin=None, shops_root=None, auth_path=None) -> dict:
    """Make a new shop and set its PIN. Returns {"name", "pin", "pin_generated"}; the PIN is shown to the operator once."""
    if not shops.valid_name(name):
        raise ValueError("A shop's name uses lower case letters, digits, - and _, 2 to 40 characters, starting with a letter or digit.")
    title = _clean_title(display_name)
    if name in shops.list_folders(shops_root) or shops.shop_dir(name, shops_root).exists():
        raise ValueError("A shop with that name already exists.")
    source = None
    if template not in (None, "", "blank"):
        if not shops.valid_name(template) or not shops.exists(template, shops_root):
            raise ValueError("The shop to copy from does not exist.")
        source = shops.shop_dir(template, shops_root)
    the_pin, generated = _pin_or_generate(pin)

    base = shops_root or shops.SHOPS_DIR
    base.mkdir(parents=True, exist_ok=True)
    hidden = base / f".new-{name}"                       # not a valid shop name, so the agent never lists it
    if hidden.exists():
        shutil.rmtree(hidden)
    try:
        if source is None:
            _write_blank(hidden, title)
        else:
            _copy_template(source, hidden, title)
        os.rename(hidden, shops.shop_dir(name, shops_root))
    except Exception:
        shutil.rmtree(hidden, ignore_errors=True)
        raise
    auth.set_pin(name, the_pin, auth_path)
    return {"name": name, "pin": the_pin, "pin_generated": generated}


# ---------------------------------------------------------------- pin

def set_pin(shop, pin=None, shops_root=None, auth_path=None) -> dict:
    _check_shop(shop, shops_root)
    the_pin, generated = _pin_or_generate(pin)
    auth.set_pin(shop, the_pin, auth_path)
    return {"pin": the_pin, "pin_generated": generated}


# ---------------------------------------------------------------- read for the editor

def _read_config(folder: Path) -> dict:
    try:
        config = yaml.safe_load((folder / "config.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        raise ValueError("This shop's config.yaml cannot be read, so it cannot be edited here. Fix the file first.") from None
    if not isinstance(config, dict):
        raise ValueError("This shop's config.yaml cannot be read, so it cannot be edited here. Fix the file first.")
    return config


def _stock_items(folder: Path) -> list:
    try:
        data = json.loads((folder / "stock.json").read_text(encoding="utf-8"))
        items = data["items"]
        return items if isinstance(items, list) else []
    except (OSError, ValueError, KeyError, TypeError):
        return []


def get_shop(shop, shops_root=None) -> dict:
    folder = _check_shop(shop, shops_root)
    config = _read_config(folder)
    items = [{"sku": i.get("sku"), "name": (i.get("name") or {}).get("en", ""), "unit": i.get("unit"),
              "price": i.get("price"), "in_stock": i.get("in_stock")} for i in _stock_items(folder) if isinstance(i, dict)]
    return {"name": shop, "display_name": shops.display_name(shop, shops_root),
            "system_prompt": config.get("system_prompt") or "", "stock": items}


# ---------------------------------------------------------------- prompt

def save_prompt(shop, system_prompt, display_name, shops_root=None) -> dict:
    folder = _check_shop(shop, shops_root)
    title = _clean_title(display_name)
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("The system prompt cannot be empty: it is the agent's instructions for this shop.")
    if len(system_prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"The system prompt can be at most {MAX_PROMPT_CHARS} characters.")
    config = _read_config(folder)
    shutil.copyfile(folder / "config.yaml", folder / "config.yaml.bak")
    config["display_name"] = title
    config["system_prompt"] = system_prompt.rstrip() + "\n"
    _atomic_write(folder / "config.yaml", yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=100))
    return {"display_name": title}


# ---------------------------------------------------------------- stock

def save_stock(shop, update=None, remove=None, add=None, shops_root=None) -> dict:
    """update: [{sku, price?, in_stock?}], remove: [sku], add: [full item]. All or nothing."""
    folder = _check_shop(shop, shops_root)
    path = folder / "stock.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data["items"]
        assert isinstance(items, list)
    except (OSError, ValueError, KeyError, AssertionError):
        raise ValueError("This shop's stock.json cannot be read, so it cannot be edited here. Fix the file first.") from None
    by_sku = {i.get("sku"): i for i in items if isinstance(i, dict)}

    for change in update or []:
        item = by_sku.get(change.get("sku")) if isinstance(change, dict) else None
        if item is None:
            raise ValueError(f"There is no item {change.get('sku') if isinstance(change, dict) else change!r} to change.")
        if "price" in change:
            price = change["price"]
            if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
                raise ValueError(f"{item['sku']}: the price must be a number above zero.")
            item["price"] = price
        if "in_stock" in change:
            if not isinstance(change["in_stock"], bool):
                raise ValueError(f"{item['sku']}: in stock must be yes or no.")
            item["in_stock"] = change["in_stock"]
    gone = set(remove or [])
    unknown = gone - set(by_sku)
    if unknown:
        raise ValueError(f"There is no item {sorted(unknown)[0]!r} to remove.")
    items = [i for i in items if not (isinstance(i, dict) and i.get("sku") in gone)]
    for new in add or []:
        if not isinstance(new, dict) or new.get("sku") in {i.get("sku") for i in items}:
            raise ValueError(f"Item {new.get('sku') if isinstance(new, dict) else new!r} is already in the stock list.")
        items.append(new)

    problems = stock.validate(items)
    if problems:
        raise ValueError("The stock list would not be valid:\n" + "\n".join(problems[:6]))
    data["items"] = items
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    _atomic_write(folder / "knowledge" / "products_pricing.md", stock.render_products_md(items))
    return {"items": len(items)}


# ---------------------------------------------------------------- solved problems

def _state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data.get("dismissed"), dict) else {"dismissed": {}}
    except (OSError, ValueError, AttributeError):
        return {"dismissed": {}}


def dismissed(state_path: Path | None = None) -> dict:
    return dict(_state(state_path or STATE_FILE)["dismissed"])


def _write_state(state: dict, path: Path) -> None:
    _atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def dismiss(problem_id, note="", shops_root=None, orders_root=None, auth_path=None, state_path=None) -> dict:
    """Mark a warning as dealt with. It stays listed (under Solved) and stops counting; an error cannot be dismissed."""
    shop = problem_id.split(":", 1)[0] if isinstance(problem_id, str) else ""
    if not shops.valid_name(shop) or ":" not in problem_id:
        raise ValueError("That is not a problem this dashboard knows.")
    _check_shop(shop, shops_root)
    current = {p["id"]: p for p in shop_health.check(shop, shops_root, orders_root, auth_path)}
    problem = current.get(problem_id)
    if problem is None:
        raise ValueError("That problem is no longer there.")
    if problem["severity"] == shop_health.ERROR:
        raise ValueError("An error cannot be marked solved: the shop cannot work until it is fixed.")
    path = state_path or STATE_FILE
    state = _state(path)
    state["dismissed"][problem_id] = {"at": datetime.now(store.IST).isoformat(), "note": str(note or "")[:200]}
    _write_state(state, path)
    return {"id": problem_id}


def restore(problem_id, state_path=None) -> dict:
    path = state_path or STATE_FILE
    state = _state(path)
    if state["dismissed"].pop(problem_id, None) is None:
        raise ValueError("That problem was not marked solved.")
    _write_state(state, path)
    return {"id": problem_id}


# ---------------------------------------------------------------- the activity log

def log_event(kind: str, shop, detail: str = "", path: Path | None = None) -> None:
    """Append one line saying what was done. Never raises into the caller's way: a change that was made stays made."""
    entry = {"at": datetime.now(store.IST).isoformat(), "kind": str(kind)[:40], "shop": shop if isinstance(shop, str) else None,
             "detail": str(detail or "")[:MAX_DETAIL_CHARS]}
    path = path or LOG_FILE
    with _log_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_activity(limit: int = 30, path: Path | None = None) -> list:
    """The latest entries, newest first. A damaged or missing log reads as empty; a damaged line is skipped."""
    path = path or LOG_FILE
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - LOG_TAIL_BYTES))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = tail.splitlines()
    if size > LOG_TAIL_BYTES and lines:
        lines = lines[1:]                                    # the first line of a cut tail is probably half a line
    out = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("at") and entry.get("kind"):
            out.append({"at": entry["at"], "kind": entry["kind"], "shop": entry.get("shop"), "detail": entry.get("detail", "")})
            if len(out) >= limit:
                break
    return out
