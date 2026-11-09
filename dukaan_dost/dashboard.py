"""
dashboard.py

The shopkeeper dashboard's HTTP side (DEC-034). It plugs into the call server as an
HTTP handler (transport_websocket.WebSocketTransport.add_http_handler) so everything is
served from one port:

    GET /s/<shop>/dashboard                the page (HTML), or the sign-in page when not signed in
    GET /s/<shop>/dashboard/data           the JSON the page polls every few seconds
    GET /s/<shop>/dashboard/session[/keep] the sign-in call the sign-in page makes (login.py, DEC-050)
    GET /s/<shop>/dashboard/signout        ends this browser's session

The page and the data need a session (the sign-in page gives one) or, for a script, HTTP Basic auth: the
shop's PIN as the password (any user name), or the user "admin" with the admin password. Every response is
marked no-store, and the page runs under a content security policy that only allows its own scripts and server.

It is read-only. The admin dashboard (adding shops, fixing errors) comes later and will
need writes, which this module deliberately cannot do.
"""

import html
import json
import re
from pathlib import Path

from . import auth, login, shops, store, webpage
from .login import SECURITY_HEADERS, Reply          # the reply type and headers live in login.py; re-exported here for the admin page

PAGE_PATH = Path(__file__).parent / "web" / "dashboard.html"
ROUTE = re.compile(r"^/s/(?P<shop>[^/]+)/dashboard(?P<sub>/data|/session/keep|/session|/signout)?/?$")
THROTTLE = auth.Throttle(max_failures=5, lock_sec=60.0)

def _text(status: int, message: str, headers: dict | None = None) -> Reply:
    return login.text_reply(status, message, headers)


def _live_for(shop: str, live_calls) -> list:
    """This shop's calls in progress, from the transport: how long each has lasted, by which line it came in, and what is
    being said and ordered right now (live_feed.py: in memory only, nothing saved). Only the signed-in dashboard gets this
    (handle() has already checked the sign-in); a transport that keeps no feed gives just the length."""
    if live_calls is None:
        return []
    try:
        return [{"seconds": int(c.get("seconds", 0)), "channel": c.get("channel") or "browser", "language": c.get("language"),
                 "lines": c.get("lines") or [], "order": c.get("order"), "loan": c.get("loan")}
                for c in live_calls() if c.get("shop") == shop]
    except Exception:
        return []


def handle(path: str, headers, remote: str, shops_root: Path | None = None,
           orders_root: Path | None = None, throttle: auth.Throttle | None = None,
           live_calls=None, sessions: auth.SessionStore | None = None) -> Reply | None:
    """A Reply for dashboard paths, or None for anything else (so other handlers can try)."""
    m = ROUTE.match(path.split("?", 1)[0])
    if m is None:
        return None
    shop = m.group("shop")
    if not shops.exists(shop, shops_root):
        return _text(404, "No such shop.")

    throttle = throttle or THROTTLE
    sessions = sessions or login.SESSIONS
    key = (remote, shop)
    title = shops.display_name(shop, shops_root)
    challenge = {"WWW-Authenticate": f'Basic realm="Dukaan Dost: {shop}", charset="UTF-8"'}
    sub = m.group("sub")

    def scope_for(user, secret):
        if user == "admin" and auth.check_admin(secret):
            return "admin"
        return f"shop:{shop}" if auth.check_pin(shop, secret) else None

    if sub in ("/session", "/session/keep"):
        return login.sign_in(headers, remote, throttle=throttle, key=key, scope_for=scope_for, sessions=sessions, keep=sub == "/session/keep")
    if sub == "/signout":
        return login.sign_out(headers, sessions)

    def sign_in_page():
        return login.render_page("shop", title, f"/s/{shop}/dashboard/session", f"/s/{shop}/", no_pin=not auth.has_pin(shop))

    creds = auth.parse_basic(headers.get("Authorization"))
    if creds is not None:                                          # a script: the header on every request, as before
        if not throttle.allowed(key):
            return _text(429, "Too many wrong attempts. Wait a minute and try again.", {"Retry-After": "60"})
        if scope_for(*creds) is None:
            throttle.fail(key)
            return login.unauthorized(headers, "That PIN is not right.", challenge, sign_in_page)
        throttle.ok(key)
    elif not auth.scope_allows(login.current_scope(headers, sessions), shop):
        return login.unauthorized(headers, "Sign in with this shop's PIN.", challenge, sign_in_page)

    if sub == "/data":
        payload = store.snapshot(shop, root=orders_root)
        payload["title"] = title
        payload["live"] = _live_for(shop, live_calls)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return Reply(200, "application/json; charset=utf-8", body, dict(SECURITY_HEADERS))

    try:
        page = webpage.load(PAGE_PATH).replace("{{SHOP}}", html.escape(title))     # the page, with its components stitched in
    except (OSError, webpage.ComponentError):
        return _text(500, "The dashboard page could not be built.")
    return Reply(200, "text/html; charset=utf-8", page.encode("utf-8"), dict(SECURITY_HEADERS))
