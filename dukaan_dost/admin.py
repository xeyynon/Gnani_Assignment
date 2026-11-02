"""
admin.py

The admin dashboard's server side (DEC-034, DEC-042): one page that shows every shop and lets the operator look
after them, and the data and commands behind it.

    GET /admin         the page
    GET /admin/data    the numbers and the problems, as JSON
    GET /admin/token   a short-lived token for the command socket (below)
    WS  /admin/ws      commands that change things (admin_actions.py)

Sign-in is the admin password only (user name "admin", password ADMIN_PASSWORD). A shop's PIN does NOT open this
page, because it shows every shop. With no ADMIN_PASSWORD set every admin route answers 503 and says how to set
one: it fails closed, never open. Wrong guesses are throttled like the shop dashboards (five in a row from one
address lock that address for a minute).

How changes are made. The HTTP layer here cannot read request bodies, so the page sends its commands over a
WebSocket as JSON: {"id": 1, "cmd": "set_pin", "shop": "alpha", "pin": "1234"} and gets back
{"id": 1, "ok": true, ...} or {"id": 1, "ok": false, "error": "..."}. A socket cannot send the browser's cached
password the way a page request does, so the page first fetches /admin/token (an ordinary signed-in request) and
opens the socket with it. The token is random, lives ten minutes, and is useless to another site: it can only be
read by a page that is itself signed in (same origin), and the socket also refuses a connection whose Origin is
not this server. That is what stops a page on another site from driving the admin socket (cross-site WebSocket
hijacking).

What a shop's row holds comes from files that exist today: the shop folder (its name, its checks), the order
files (today's orders, the last order) and the transport (a call in progress). Nothing is
invented: a shop with no orders shows zeros and "no orders yet", not an estimate.

A problem marked solved (admin_actions.dismiss) stays listed under "solved" and stops counting; if the problem
goes away by itself it simply drops out. Errors cannot be marked solved.
"""

import asyncio
import html
import json
import logging
import re
import secrets
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from . import admin_actions, auth, shop_health, shops, store, webpage
from .dashboard import SECURITY_HEADERS, Reply, _text

log = logging.getLogger("admin")

PAGE_PATH = Path(__file__).parent / "web" / "admin.html"
ROUTE = re.compile(r"^/admin(?P<sub>/data|/token)?/?$")
WS_PATH = "/admin/ws"
THROTTLE = auth.Throttle(max_failures=5, lock_sec=60.0)
ADMIN_USER = "admin"
TOKEN_TTL_SEC = 600
MAX_TOKENS = 50
HELLO_TIMEOUT_SEC = 10
COMMANDS_PER_MINUTE = 60

# A shop's overall state, worst first: any error, else any warning, else ready.
READY, ATTENTION, BROKEN = "ready", "attention", "broken"


def _state(problems: list) -> str:
    if any(p["severity"] == shop_health.ERROR for p in problems):
        return BROKEN
    return ATTENTION if problems else READY


def _live_seconds(shop: str, live_calls) -> list:
    """How long each call in progress for this shop has been going, in seconds. Nothing else about a call is shared."""
    if live_calls is None:
        return []
    try:
        return [int(c.get("seconds", 0)) for c in live_calls() if c.get("shop") == shop]
    except Exception:
        return []


def snapshot(shops_root: Path | None = None, orders_root: Path | None = None, live_calls=None,
             now: datetime | None = None, auth_path: Path | None = None, state_path: Path | None = None,
             log_path: Path | None = None) -> dict:
    """Everything the admin page shows, in one JSON-ready dict."""
    marked = admin_actions.dismissed(state_path)
    rows, problems, solved = [], [], []
    totals = {"orders_today": 0, "live_calls": 0}
    for name in shops.list_folders(shops_root):          # every shop-like folder, including one with no config.yaml
        found = shop_health.check(name, shops_root, orders_root, auth_path)
        active = [p for p in found if p["id"] not in marked]
        solved += [dict(p, note=marked[p["id"]].get("note", ""), at=marked[p["id"]].get("at")) for p in found if p["id"] in marked]
        snap = store.snapshot(name, now=now, root=orders_root, limit=1)
        summary = snap["summary"]
        live = _live_seconds(name, live_calls)
        rows.append({
            "name": name,
            "title": shops.display_name(name, shops_root),
            "state": _state(active),
            "has_pin": auth.has_pin(name, auth_path),
            "live": live,
            "orders_today": summary["orders_today"],
            "orders_total": summary["orders_total"],
            "last_order": snap["orders"][0]["time"] if snap["orders"] else None,
            "problems": len(active),
        })
        problems += active
        totals["orders_today"] += summary["orders_today"]
        totals["live_calls"] += len(live)
    problems.sort(key=lambda p: (shop_health.SEVERITY_ORDER.get(p["severity"], 9), p["shop"], p["id"]))
    totals.update({
        "shops": len(rows),
        "shops_ready": sum(1 for r in rows if r["state"] == READY),
        "shops_attention": sum(1 for r in rows if r["state"] == ATTENTION),
        "shops_broken": sum(1 for r in rows if r["state"] == BROKEN),
        "errors": sum(1 for p in problems if p["severity"] == shop_health.ERROR),
        "warnings": sum(1 for p in problems if p["severity"] == shop_health.WARNING),
    })
    return {"generated_at": (now or datetime.now(store.IST)).astimezone(store.IST).isoformat(),
            "totals": totals, "shops": rows, "problems": problems, "solved": solved,
            "activity": admin_actions.recent_activity(30, log_path)}


# ---------------------------------------------------------------- the socket's token

class TokenStore:
    """Short-lived random tokens that let a signed-in page open the command socket."""

    def __init__(self, ttl: float = TOKEN_TTL_SEC, clock=time.monotonic):
        self._ttl, self._clock, self._tokens = ttl, clock, {}

    def issue(self) -> str:
        now = self._clock()
        self._tokens = {t: until for t, until in self._tokens.items() if until > now}
        while len(self._tokens) >= MAX_TOKENS:                       # never grow without bound: drop the oldest
            self._tokens.pop(min(self._tokens, key=self._tokens.get))
        token = secrets.token_urlsafe(32)
        self._tokens[token] = now + self._ttl
        return token

    def valid(self, token) -> bool:
        until = self._tokens.get(token) if isinstance(token, str) else None
        return until is not None and until > self._clock()


TOKENS = TokenStore()


# ---------------------------------------------------------------- the pages

def handle(path: str, headers, remote: str, shops_root: Path | None = None, orders_root: Path | None = None,
           throttle: auth.Throttle | None = None, live_calls=None, auth_path: Path | None = None,
           state_path: Path | None = None, tokens: TokenStore | None = None, log_path: Path | None = None) -> Reply | None:
    """A Reply for the admin paths, or None for anything else (so other handlers can try)."""
    m = ROUTE.match(path.split("?", 1)[0])
    if m is None:
        return None

    if not auth.check_admin_configured():
        return _text(503, "The admin dashboard is off. Set ADMIN_PASSWORD (in .env or local_config.py) and restart the agent.")

    throttle = throttle or THROTTLE
    key = (remote, "admin")
    challenge = {"WWW-Authenticate": 'Basic realm="Dukaan Dost admin", charset="UTF-8"'}
    if not throttle.allowed(key):
        return _text(429, "Too many wrong attempts. Wait a minute and try again.", {"Retry-After": "60"})
    creds = auth.parse_basic(headers.get("Authorization"))
    if creds is None:
        return _text(401, "Sign in as admin.", challenge)
    user, secret = creds
    if user == ADMIN_USER and auth.check_admin(secret):
        throttle.ok(key)
    else:
        throttle.fail(key)
        return _text(401, "That is not the admin password.", challenge)

    sub = m.group("sub")
    if sub == "/token":
        body = json.dumps({"token": (tokens or TOKENS).issue()}).encode("utf-8")
        return Reply(200, "application/json; charset=utf-8", body, dict(SECURITY_HEADERS))
    if sub == "/data":
        body = json.dumps(snapshot(shops_root, orders_root, live_calls, auth_path=auth_path, state_path=state_path, log_path=log_path),
                          ensure_ascii=False).encode("utf-8")
        return Reply(200, "application/json; charset=utf-8", body, dict(SECURITY_HEADERS))
    try:
        page = webpage.load(PAGE_PATH).replace("{{SHOP}}", html.escape("Admin"))
    except (OSError, webpage.ComponentError):
        return _text(500, "The admin page could not be built.")
    return Reply(200, "text/html; charset=utf-8", page.encode("utf-8"), dict(SECURITY_HEADERS))


# ---------------------------------------------------------------- the command socket

def origin_ok(headers) -> bool:
    """A browser always sends Origin on a WebSocket; it must name this server. (No Origin means not a browser: the token still applies.)"""
    origin = headers.get("Origin")
    if origin is None:
        return True
    host = headers.get("Host")
    return bool(host) and urlsplit(origin).netloc == host


def run_command(msg: dict, shops_root=None, orders_root=None, auth_path=None, state_path=None) -> dict:
    """Do one command and return its result fields. Raises ValueError for anything the operator should be told."""
    cmd = msg.get("cmd")
    if cmd == "create_shop":
        return admin_actions.create_shop(msg.get("name"), msg.get("display_name"), msg.get("template") or "blank",
                                         msg.get("pin") or None, shops_root, auth_path)
    if cmd == "set_pin":
        return admin_actions.set_pin(msg.get("shop"), msg.get("pin") or None, shops_root, auth_path)
    if cmd == "get_shop":
        return admin_actions.get_shop(msg.get("shop"), shops_root)
    if cmd == "save_prompt":
        return admin_actions.save_prompt(msg.get("shop"), msg.get("system_prompt"), msg.get("display_name"), shops_root)
    if cmd == "save_stock":
        return admin_actions.save_stock(msg.get("shop"), msg.get("update"), msg.get("remove"), msg.get("add"), shops_root)
    if cmd == "dismiss":
        return admin_actions.dismiss(msg.get("id"), msg.get("note", ""), shops_root, orders_root, auth_path, state_path)
    if cmd == "restore":
        return admin_actions.restore(msg.get("id"), state_path)
    raise ValueError("That command is not known.")


CHANGES_A_SHOP = {"create_shop", "save_prompt", "save_stock", "set_pin"}


def describe(msg: dict, result: dict):
    """(shop, what was done) for the activity log, or None for a command that changes nothing. Never includes a PIN or a prompt."""
    cmd = msg.get("cmd")
    pin_how = "made up" if result.get("pin_generated") else "chosen"
    if cmd == "create_shop":
        template = msg.get("template") or "blank"
        return result.get("name"), ("created as a blank shop" if template == "blank" else f"created as a copy of {template}") + f"; PIN {pin_how}"
    if cmd == "set_pin":
        return msg.get("shop"), f"PIN changed ({pin_how})"
    if cmd == "save_prompt":
        return msg.get("shop"), "name and instructions saved"
    if cmd == "save_stock":
        n = lambda key: len(msg.get(key) or [])
        return msg.get("shop"), f"stock saved: {n('update')} changed, {n('remove')} removed, {n('add')} added"
    if cmd == "dismiss":
        pid = str(msg.get("id") or "")
        note = str(msg.get("note") or "").strip()
        return pid.split(":", 1)[0], f"marked solved: {pid}" + (f" ({note})" if note else "")
    if cmd == "restore":
        pid = str(msg.get("id") or "")
        return pid.split(":", 1)[0], f"brought back: {pid}"
    return None


def make_ws_handler(shops_root=None, orders_root=None, auth_path=None, state_path=None, tokens: TokenStore | None = None,
                    on_change=None, log_path: Path | None = None):
    """The async handler for WS /admin/ws. `on_change(shop)` is called after a command changed a shop, so a running
    agent can drop what it cached for it."""
    tokens = tokens or TOKENS

    async def handler(ws):
        if not auth.check_admin_configured() or not origin_ok(ws.request.headers):
            await ws.close(1008, "not allowed")
            return
        try:
            hello = json.loads(await asyncio.wait_for(ws.recv(), HELLO_TIMEOUT_SEC))
        except (asyncio.TimeoutError, ValueError, TypeError):
            await ws.close(1008, "sign-in needed")
            return
        if not isinstance(hello, dict) or hello.get("cmd") != "hello" or not tokens.valid(hello.get("token")):
            await ws.close(1008, "sign-in needed")
            return
        await ws.send(json.dumps({"type": "ready"}))

        recent = []
        async for raw in ws:
            try:
                msg = json.loads(raw)
                if not isinstance(msg, dict):
                    raise ValueError
            except (ValueError, TypeError):
                continue
            reply = {"id": msg.get("id")}
            now = time.monotonic()
            recent = [t for t in recent if now - t < 60]
            if len(recent) >= COMMANDS_PER_MINUTE:
                reply.update(ok=False, error="Too many commands. Wait a moment.")
            else:
                recent.append(now)
                try:
                    result = await asyncio.to_thread(run_command, msg, shops_root, orders_root, auth_path, state_path)
                    reply.update(ok=True, **{k: v for k, v in result.items() if k not in ("ok", "id")})
                    what = describe(msg, result)
                    if what is not None:
                        try:
                            admin_actions.log_event(msg.get("cmd"), what[0], what[1], log_path)
                        except Exception:
                            log.exception("[ADMIN] could not write the activity log")
                    if msg.get("cmd") in CHANGES_A_SHOP and on_change is not None:
                        try:
                            on_change(msg.get("shop") or msg.get("name"))
                        except Exception:
                            log.exception("[ADMIN] on_change failed")
                except ValueError as e:
                    reply.update(ok=False, error=str(e))
                except Exception:
                    log.exception("[ADMIN] command failed")
                    reply.update(ok=False, error="Something went wrong and nothing was changed. See the agent's log.")
            await ws.send(json.dumps(reply, ensure_ascii=False))

    return handler
