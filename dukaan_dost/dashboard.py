"""
dashboard.py

The shopkeeper dashboard's HTTP side (DEC-034). It plugs into the call server as an
HTTP handler (transport_websocket.WebSocketTransport.add_http_handler) so everything is
served from one port:

    GET /s/<shop>/dashboard        the page (HTML)
    GET /s/<shop>/dashboard/data   the JSON the page polls every few seconds

Both need HTTP Basic auth: the shop's PIN as the password (any user name), or the user
"admin" with the admin password. Every response is marked no-store, and the page runs
under a content security policy that only allows its own scripts and server.

It is read-only. The admin dashboard (adding shops, fixing errors) comes later and will
need writes, which this module deliberately cannot do.
"""

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import auth, shops, store, webpage

PAGE_PATH = Path(__file__).parent / "web" / "dashboard.html"
ROUTE = re.compile(r"^/s/(?P<shop>[^/]+)/dashboard(?P<data>/data)?/?$")
THROTTLE = auth.Throttle(max_failures=5, lock_sec=60.0)

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
}


@dataclass
class Reply:
    status: int
    content_type: str
    body: bytes
    headers: dict = field(default_factory=dict)


def _text(status: int, message: str, headers: dict | None = None) -> Reply:
    return Reply(status, "text/plain; charset=utf-8", (message + "\n").encode("utf-8"),
                 {**SECURITY_HEADERS, **(headers or {})})


def _live_for(shop: str, live_calls) -> list:
    """This shop's calls in progress, from the transport. Only the length of each call is shared."""
    if live_calls is None:
        return []
    try:
        return [{"seconds": int(c.get("seconds", 0))} for c in live_calls() if c.get("shop") == shop]
    except Exception:
        return []


def handle(path: str, headers, remote: str, shops_root: Path | None = None,
           orders_root: Path | None = None, throttle: auth.Throttle | None = None,
           live_calls=None) -> Reply | None:
    """A Reply for dashboard paths, or None for anything else (so other handlers can try)."""
    m = ROUTE.match(path.split("?", 1)[0])
    if m is None:
        return None
    shop = m.group("shop")
    if not shops.exists(shop, shops_root):
        return _text(404, "No such shop.")

    throttle = throttle or THROTTLE
    key = (remote, shop)
    challenge = {"WWW-Authenticate": f'Basic realm="Dukaan Dost: {shop}", charset="UTF-8"'}
    if not throttle.allowed(key):
        return _text(429, "Too many wrong attempts. Wait a minute and try again.", {"Retry-After": "60"})
    creds = auth.parse_basic(headers.get("Authorization"))
    if creds is None:
        return _text(401, "Sign in with this shop's PIN.", challenge)
    user, secret = creds
    if (user == "admin" and auth.check_admin(secret)) or auth.check_pin(shop, secret):
        throttle.ok(key)
    else:
        throttle.fail(key)
        return _text(401, "That PIN is not right.", challenge)

    title = shops.display_name(shop, shops_root)
    if m.group("data"):
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
