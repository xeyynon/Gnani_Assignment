"""
auth.py

Sign-in for the dashboards (DEC-034): one admin password and a PIN per shop. No
accounts and no database.

  - A shop's PIN is stored hashed (scrypt, a random salt per PIN) in data/auth.json,
    which is gitignored. A shop with no PIN cannot sign in: there is no default PIN.
  - The admin password comes from the ADMIN_PASSWORD setting (env var or
    local_config.py), never from a file in the repo. Unset means no admin access.
  - A script sends them with HTTP Basic auth. The user name is the shop name (or
    "admin"); only the password is secret. A person uses the sign-in page instead, which
    sends the same header once and gets a session cookie back (SessionStore, DEC-050).
    Use https once this leaves localhost.
  - Wrong guesses are throttled: 5 failures from one address for one shop locks that
    pair for a minute.

Set a PIN:   python -m dukaan_dost.auth set-pin <shop>
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from pathlib import Path

from . import store
from .shops import PROJECT_ROOT, valid_name

AUTH_FILE = PROJECT_ROOT / "data" / "auth.json"
MIN_PIN_LENGTH = 4
SESSION_COOKIE = "dd_session"
SESSION_TTL_SEC = 12 * 3600               # a browser session: until the tab's browser closes, and at most this long on the server
REMEMBER_TTL_SEC = 30 * 24 * 3600         # "keep me signed in on this device"
MAX_SESSIONS = 500
_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)
_lock = threading.Lock()


def _hash(pin: str, salt: bytes) -> bytes:
    return hashlib.scrypt(pin.encode("utf-8"), salt=salt, **_SCRYPT)


class AuthFileUnreadable(ValueError):
    """auth.json is there but cannot be read or understood. Writing a new PIN over it would erase every other shop's PIN."""


def _load(path: Path, strict: bool = False) -> dict:
    """The PIN table. A missing file is an empty table. A file that is there but unreadable also reads as empty for
    checking a PIN (nobody gets in), but strict=True (used before writing) raises instead."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("shops"), dict):
            return data
        problem = "it has no table of shops"
    except FileNotFoundError:
        return {"shops": {}}
    except (OSError, ValueError) as e:
        problem = str(e)
    if strict:
        raise AuthFileUnreadable(f"{path} cannot be read ({problem}); fix or remove it before setting a PIN")
    return {"shops": {}}


def set_pin(shop: str, pin: str, path: Path | None = None) -> None:
    if not valid_name(shop):
        raise ValueError(f"{shop!r} is not a valid shop name")
    if not isinstance(pin, str) or len(pin) < MIN_PIN_LENGTH:
        raise ValueError(f"A PIN needs at least {MIN_PIN_LENGTH} characters")
    path = path or AUTH_FILE
    salt = secrets.token_bytes(16)
    with _lock:
        data = _load(path, strict=True)
        data.setdefault("shops", {})[shop] = {"salt": salt.hex(), "hash": _hash(pin, salt).hex()}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        store.replace_file(tmp, path)


def has_pin(shop: str, path: Path | None = None) -> bool:
    return shop in _load(path or AUTH_FILE).get("shops", {})


def check_pin(shop: str, pin: str, path: Path | None = None) -> bool:
    entry = _load(path or AUTH_FILE).get("shops", {}).get(shop)
    if not entry or not isinstance(entry, dict) or not isinstance(pin, str):
        return False
    try:
        expected = bytes.fromhex(entry["hash"])
        salt = bytes.fromhex(entry["salt"])
    except (KeyError, ValueError):
        return False
    return hmac.compare_digest(_hash(pin, salt), expected)


def check_admin_configured() -> bool:
    """Is an admin password set at all? (The placeholder from local_config.example.py does not count.)"""
    configured = os.environ.get("ADMIN_PASSWORD", "")
    return bool(configured) and not configured.startswith("your-")


def check_admin(password: str) -> bool:
    configured = os.environ.get("ADMIN_PASSWORD", "")
    if not configured or configured.startswith("your-") or not isinstance(password, str):
        return False
    return hmac.compare_digest(password.encode("utf-8"), configured.encode("utf-8"))


def parse_basic(header: str | None):
    """(user, password) from an `Authorization: Basic ...` header, or None."""
    if not header or not header.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    user, sep, password = decoded.partition(":")
    return (user, password) if sep else None


def cookie_value(header: str | None, name: str = SESSION_COOKIE):
    """The value of one cookie from a `Cookie:` header, or None."""
    for part in (header or "").split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key == name:
            return value
    return None


def session_cookie(token: str, max_age: int | None = None, secure: bool = False) -> str:
    """The Set-Cookie value for a signed-in browser: not readable by scripts, never sent from another site."""
    parts = [f"{SESSION_COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Strict"]
    if max_age is not None:
        parts.append(f"Max-Age={int(max_age)}")
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def clear_cookie(secure: bool = False) -> str:
    return session_cookie("", 0, secure)


def scope_allows(scope, shop: str | None) -> bool:
    """May a session of this scope open this page? The admin may open any shop; a shop only its own. `shop` None means the admin page."""
    if scope == "admin":
        return True
    return shop is not None and scope == f"shop:{shop}"


class SessionStore:
    """Signed-in browsers. A token is random, held only in memory (a restart signs everyone out) and bound to one scope:
    "admin" or "shop:<name>". It proves the page was signed in; it is not the PIN, and it dies at its time limit or on sign-out."""

    def __init__(self, clock=time.monotonic, max_sessions: int = MAX_SESSIONS):
        self._clock, self._max = clock, max_sessions
        self._sessions = {}                       # token -> (scope, expires)
        self._lock = threading.Lock()

    def issue(self, scope: str, ttl: float = SESSION_TTL_SEC) -> str:
        now = self._clock()
        with self._lock:
            self._sessions = {t: v for t, v in self._sessions.items() if v[1] > now}
            while len(self._sessions) >= self._max:             # never grow without bound: drop the one nearest its end
                self._sessions.pop(min(self._sessions, key=lambda t: self._sessions[t][1]))
            token = secrets.token_urlsafe(32)
            self._sessions[token] = (scope, now + ttl)
            return token

    def scope_of(self, token):
        if not isinstance(token, str) or not token:
            return None
        with self._lock:
            entry = self._sessions.get(token)
            if entry is None:
                return None
            if entry[1] <= self._clock():
                del self._sessions[token]
                return None
            return entry[0]

    def revoke(self, token) -> None:
        with self._lock:
            self._sessions.pop(token, None)


class Throttle:
    """Locks a key for `lock_sec` after `max_failures` wrong guesses in a row."""

    def __init__(self, max_failures: int = 5, lock_sec: float = 60.0, clock=time.monotonic):
        self.max_failures = max_failures
        self.lock_sec = lock_sec
        self._clock = clock
        self._failures = {}
        self._locked_until = {}
        self._lock = threading.Lock()

    def allowed(self, key) -> bool:
        with self._lock:
            until = self._locked_until.get(key)
            if until is None:
                return True
            if self._clock() >= until:
                del self._locked_until[key]
                self._failures.pop(key, None)
                return True
            return False

    def fail(self, key) -> None:
        with self._lock:
            self._failures[key] = self._failures.get(key, 0) + 1
            if self._failures[key] >= self.max_failures:
                self._locked_until[key] = self._clock() + self.lock_sec

    def ok(self, key) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def remaining(self, key) -> int:
        """Wrong guesses left before the lock."""
        with self._lock:
            return max(0, self.max_failures - self._failures.get(key, 0))

    def seconds_left(self, key) -> int:
        """Seconds until a locked key may try again (0 if it is not locked)."""
        with self._lock:
            until = self._locked_until.get(key)
            return 0 if until is None else max(0, int(until - self._clock() + 0.999))


def _main(argv) -> int:
    import getpass
    if len(argv) != 3 or argv[1] != "set-pin":
        print("usage: python -m dukaan_dost.auth set-pin <shop>")
        return 2
    shop = argv[2]
    pin = getpass.getpass(f"New PIN for {shop}: ")
    if pin != getpass.getpass("Again: "):
        print("The two entries differ; nothing was changed.")
        return 1
    try:
        set_pin(shop, pin)
    except ValueError as e:
        print(e)
        return 1
    print(f"PIN set for {shop}. It is stored hashed in {AUTH_FILE}.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
