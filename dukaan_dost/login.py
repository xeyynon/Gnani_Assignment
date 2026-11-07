"""
login.py

The sign-in page and the session endpoints, shared by the shopkeeper dashboard and the admin page (DEC-050).

Why a page and not the browser's own prompt: the prompt cannot say whose dashboard it is, cannot show a PIN pad,
cannot say how many tries are left, and looks like an error. The page can, and it works with a password manager.

How it signs in. The server behind this one answers GET only, so the page signs in with a single GET whose
Authorization header carries the PIN (the same header a script uses), never a URL. The reply sets a cookie that is
unreadable by scripts and never sent from another site (HttpOnly, SameSite=Strict). From then on the cookie is enough.
Sessions live in memory (auth.SessionStore): a restart signs everyone out, which is the safe direction.

What "not signed in" answers, by who is asking:
    a person's browser opening the page       the sign-in page (status 401, no WWW-Authenticate, so no native prompt)
    the page's own background request         401, no challenge (the page then offers to sign in again)
    a script or a test, no browser at all     401 with WWW-Authenticate: Basic, exactly as before
So the older way (an Authorization header on every request) still works for tools.
"""

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import auth, webpage

PAGE_PATH = Path(__file__).parent / "web" / "login.html"
SESSIONS = auth.SessionStore()

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


def text_reply(status: int, message: str, headers: dict | None = None) -> Reply:
    return Reply(status, "text/plain; charset=utf-8", (message + "\n").encode("utf-8"),
                 {**SECURITY_HEADERS, **(headers or {})})


def json_reply(status: int, payload: dict, headers: dict | None = None) -> Reply:
    return Reply(status, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"),
                 {**SECURITY_HEADERS, **(headers or {})})


def client_kind(headers) -> str:
    """"page" (a browser opening a page), "script" (a browser page's own background request) or "tool" (no browser)."""
    dest = headers.get("Sec-Fetch-Dest")
    if dest:
        return "page" if dest == "document" else "script"
    return "page" if "text/html" in (headers.get("Accept") or "") else "tool"


def current_scope(headers, sessions: auth.SessionStore | None = None):
    token = auth.cookie_value(headers.get("Cookie"))
    return (sessions or SESSIONS).scope_of(token) if token else None


def _secure(headers) -> bool:
    return (headers.get("X-Forwarded-Proto") or "").lower() == "https"


def render_page(kind: str, title: str, session_url: str, back_url: str = "", no_pin: bool = False) -> Reply:
    """The sign-in page for one shop (kind "shop") or the admin (kind "admin"). Every value is escaped."""
    try:
        page = webpage.load(PAGE_PATH)
    except (OSError, webpage.ComponentError):
        return text_reply(500, "The sign-in page could not be built.")
    values = {"KIND": kind, "TITLE": title, "SESSION_URL": session_url, "BACK_URL": back_url, "NOPIN": "1" if no_pin else "0",
              "THEME": "dark" if kind == "admin" else "auto"}                      # the admin starts dark, like its page
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: html.escape(values[m.group(1)], quote=True) if m.group(1) in values else m.group(0), page)
    return Reply(401, "text/html; charset=utf-8", page.encode("utf-8"), dict(SECURITY_HEADERS))


def unauthorized(headers, message: str, challenge: dict, page=None) -> Reply:
    """The answer to a request that is not signed in, by who is asking (see the top of this file)."""
    kind = client_kind(headers)
    if kind == "page" and page is not None:
        return page()
    return text_reply(401, message, challenge if kind == "tool" else None)


def _locked(throttle: auth.Throttle, key) -> Reply:
    wait = max(1, throttle.seconds_left(key))
    return json_reply(429, {"ok": False, "locked": True, "retry_after": wait}, {"Retry-After": str(wait)})


def sign_in(headers, remote: str, *, throttle: auth.Throttle, key, scope_for, sessions: auth.SessionStore | None = None,
            keep: bool = False) -> Reply:
    """The sign-in call the page makes. `scope_for(user, secret)` is "admin", "shop:<name>" or None. Wrong guesses count against `key`."""
    sessions = sessions or SESSIONS
    if not throttle.allowed(key):
        return _locked(throttle, key)
    creds = auth.parse_basic(headers.get("Authorization"))
    if creds is None:
        return json_reply(400, {"ok": False, "empty": True})
    scope = scope_for(*creds)
    if scope is None:
        throttle.fail(key)
        if not throttle.allowed(key):                                 # that was the last guess
            return _locked(throttle, key)
        return json_reply(401, {"ok": False, "wrong": True, "remaining": throttle.remaining(key)})
    throttle.ok(key)
    old = auth.cookie_value(headers.get("Cookie"))
    if old:
        sessions.revoke(old)                                          # a new sign-in replaces the old session: no pile-up, no reuse
    ttl = auth.REMEMBER_TTL_SEC if keep else auth.SESSION_TTL_SEC
    token = sessions.issue(scope, ttl)
    cookie = auth.session_cookie(token, ttl if keep else None, _secure(headers))
    return json_reply(200, {"ok": True}, {"Set-Cookie": cookie})


def sign_out(headers, sessions: auth.SessionStore | None = None) -> Reply:
    """End this browser's session and clear its cookie. Safe to call when not signed in."""
    token = auth.cookie_value(headers.get("Cookie"))
    if token:
        (sessions or SESSIONS).revoke(token)
    return json_reply(200, {"ok": True}, {"Set-Cookie": auth.clear_cookie(_secure(headers))})
