"""
Tests for the sign-in page and the session cookie (DEC-050): login.py, the session parts of auth.py, and how
the dashboard and the admin page use them.

They cover what must work (a PIN gets a session; the session opens the page and its data; sign-out ends it; a script
with an Authorization header still works) and what must not (a wrong PIN, a locked address, another shop's session,
a forged or expired cookie, a shop name with markup in it, a PIN in a URL).

    python -m pytest tests/test_login.py
"""

import base64
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import admin, auth, dashboard, demo_data, login, shops, store  # noqa: E402
from dukaan_dost.transport_websocket import WebSocketTransport  # noqa: E402


class H(dict):
    """Request headers: case-insensitive reads, written as keyword arguments (sec_fetch_dest -> Sec-Fetch-Dest)."""

    def __init__(self, **kw):
        super().__init__({k.replace("_", "-").lower(): v for k, v in kw.items()})

    def get(self, key, default=None):
        return super().get(key.lower(), default)


def basic(user, password):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode("utf-8")).decode()


BROWSER = dict(sec_fetch_dest="document", accept="text/html,application/xhtml+xml")
PAGE_FETCH = dict(sec_fetch_dest="empty", accept="*/*")


def cookie_from(reply):
    """The `dd_session=...` pair a browser would send back, from a reply's Set-Cookie."""
    return reply.headers["Set-Cookie"].split(";", 1)[0]


class Fake:
    """A clock that only moves when told to."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def env(tmp_path, monkeypatch):
    shops_root, orders_root = tmp_path / "shops", tmp_path / "orders"
    for name, display in [("alpha", "Alpha Kirana"), ("beta", "Beta Store"), ("nopin", "No Pin Shop")]:
        folder = shops_root / name
        folder.mkdir(parents=True)
        (folder / "config.yaml").write_text(
            f'system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "{display}"\n', encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)
    auth.set_pin("alpha", "1111", auth_file)
    auth.set_pin("beta", "2222", auth_file)
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    demo_data.seed("alpha", orders_root, now=datetime.now(store.IST))

    clock = Fake()
    throttle = auth.Throttle(max_failures=5, lock_sec=60, clock=clock)
    sessions = auth.SessionStore(clock=clock)

    class Env:
        pass

    e = Env()
    e.shops_root, e.orders_root, e.clock, e.throttle, e.sessions, e.tmp = shops_root, orders_root, clock, throttle, sessions, tmp_path

    def shop(path, headers=None, remote="1.2.3.4", **h):
        return dashboard.handle(path, H(**{**(headers or {}), **h}) if not isinstance(headers, H) else headers, remote,
                                shops_root=shops_root, orders_root=orders_root, throttle=throttle, sessions=sessions)

    def adm(path, headers=None, remote="1.2.3.4", **h):
        return admin.handle(path, H(**{**(headers or {}), **h}), remote, shops_root=shops_root, orders_root=orders_root,
                            throttle=throttle, sessions=sessions, auth_path=auth_file,
                            state_path=tmp_path / "state.json", log_path=tmp_path / "log.jsonl")

    e.shop, e.adm = shop, adm
    return e


# ---- the pieces ------------------------------------------------------------

def test_a_session_is_random_scoped_and_ends_at_its_time_limit():
    clock = Fake()
    s = auth.SessionStore(clock=clock)
    a, b = s.issue("shop:alpha", 100), s.issue("shop:alpha", 100)
    assert a != b and len(a) >= 40
    assert s.scope_of(a) == "shop:alpha"
    clock.now += 99
    assert s.scope_of(a) == "shop:alpha"
    clock.now += 2
    assert s.scope_of(a) is None                                      # past its time limit
    assert s.scope_of("not-a-token") is None and s.scope_of(None) is None and s.scope_of("") is None


def test_revoking_a_session_ends_it_and_revoking_twice_is_fine():
    s = auth.SessionStore()
    t = s.issue("admin")
    s.revoke(t)
    s.revoke(t)
    assert s.scope_of(t) is None


def test_the_store_never_grows_without_bound_and_drops_the_one_nearest_its_end():
    clock = Fake()
    s = auth.SessionStore(clock=clock, max_sessions=3)
    first = s.issue("admin", 10)
    others = [s.issue("admin", 1000) for _ in range(5)]
    assert s.scope_of(first) is None                                  # the shortest-lived was dropped to make room
    assert sum(1 for t in others if s.scope_of(t)) <= 3


@pytest.mark.parametrize("scope,shop,allowed", [
    ("admin", "alpha", True), ("admin", None, True), ("shop:alpha", "alpha", True),
    ("shop:alpha", "beta", False), ("shop:alpha", None, False), (None, "alpha", False), ("shop:", "alpha", False),
])
def test_which_scope_opens_which_page(scope, shop, allowed):
    assert auth.scope_allows(scope, shop) is allowed


def test_the_cookie_is_http_only_same_site_strict_and_cleared_by_max_age_zero():
    c = auth.session_cookie("tok")
    assert "HttpOnly" in c and "SameSite=Strict" in c and "Path=/" in c
    assert "Max-Age" not in c and "Secure" not in c                    # a browser session on plain http
    assert "Max-Age=60" in auth.session_cookie("tok", 60)
    assert "Secure" in auth.session_cookie("tok", None, secure=True)
    assert "Max-Age=0" in auth.clear_cookie() and auth.clear_cookie().startswith("dd_session=;")


def test_a_cookie_header_is_read_whatever_else_is_in_it():
    assert auth.cookie_value("a=1; dd_session=xyz; b=2") == "xyz"
    assert auth.cookie_value("dd_session=xyz") == "xyz"
    assert auth.cookie_value("xdd_session=nope; other=1") is None
    assert auth.cookie_value("") is None and auth.cookie_value(None) is None


def test_the_throttle_says_how_many_tries_are_left_and_how_long_to_wait():
    clock = Fake()
    t = auth.Throttle(max_failures=3, lock_sec=60, clock=clock)
    assert t.remaining("k") == 3 and t.seconds_left("k") == 0
    t.fail("k")
    assert t.remaining("k") == 2
    t.fail("k")
    t.fail("k")
    assert not t.allowed("k") and t.remaining("k") == 0 and t.seconds_left("k") == 60
    clock.now += 41
    assert t.seconds_left("k") == 19
    clock.now += 20
    assert t.allowed("k") and t.seconds_left("k") == 0


@pytest.mark.parametrize("headers,kind", [
    (dict(sec_fetch_dest="document"), "page"), (dict(sec_fetch_dest="empty"), "script"), (dict(sec_fetch_dest="iframe"), "script"),
    (dict(accept="text/html"), "page"), (dict(accept="*/*"), "tool"), ({}, "tool"),
    (dict(sec_fetch_dest="empty", accept="text/html"), "script"),         # the browser's own word beats the Accept header
])
def test_who_is_asking(headers, kind):
    assert login.client_kind(H(**headers)) == kind


# ---- what a shop dashboard answers when not signed in ----------------------

def test_a_browser_opening_the_dashboard_gets_the_sign_in_page_not_a_prompt(env):
    r = env.shop("/s/alpha/dashboard", **BROWSER)
    assert r.status == 401 and r.content_type.startswith("text/html")
    assert "WWW-Authenticate" not in r.headers                           # so the browser shows our page, never its own box
    body = r.body.decode()
    assert 'id="login"' in body and 'data-kind="shop"' in body and 'data-session="/s/alpha/dashboard/session"' in body
    assert "Alpha Kirana" in body and 'data-nopin="0"' in body
    assert r.headers["Cache-Control"] == "no-store" and "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


def test_a_pages_own_background_request_gets_a_plain_401_with_no_prompt_header(env):
    for path in ("/s/alpha/dashboard/data", "/s/alpha/dashboard"):
        r = env.shop(path, **PAGE_FETCH)
        assert r.status == 401 and "WWW-Authenticate" not in r.headers and not r.content_type.startswith("text/html")


def test_a_script_with_no_browser_still_gets_the_basic_challenge(env):
    r = env.shop("/s/alpha/dashboard")
    assert r.status == 401 and r.headers["WWW-Authenticate"].startswith("Basic ")
    r = env.shop("/s/alpha/dashboard/data", authorization=basic("x", "wrong"))
    assert r.status == 401 and "WWW-Authenticate" in r.headers


def test_a_script_with_the_right_header_is_still_let_in_even_if_it_sends_accept_html(env):
    assert env.shop("/s/alpha/dashboard/data", authorization=basic("x", "1111"), accept="text/html").status == 200


def test_a_shop_with_no_pin_says_so_on_its_sign_in_page(env):
    body = env.shop("/s/nopin/dashboard", **BROWSER).body.decode()
    assert 'data-nopin="1"' in body


def test_markup_in_a_shops_name_is_text_on_the_sign_in_page(env):
    (env.shops_root / "evil").mkdir()
    (env.shops_root / "evil" / "config.yaml").write_text(
        'system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "<img src=x onerror=alert(1)> {{SESSION_URL}}"\n', encoding="utf-8")
    body = env.shop("/s/evil/dashboard", **BROWSER).body.decode()
    assert "<img" not in body and "onerror=alert(1)>" not in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body
    assert re.search(r"<title>Sign in: .*\{\{SESSION_URL\}\}", body)       # a placeholder inside a name is not filled in a second time
    assert not re.search(r"https?://", body)                              # nothing loaded from outside


# ---- signing in ------------------------------------------------------------

def test_the_right_pin_gives_a_session_cookie_that_opens_the_page_and_its_data(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"), **PAGE_FETCH)
    assert r.status == 200 and json.loads(r.body) == {"ok": True}
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Max-Age" not in cookie
    assert "1111" not in cookie and "1111" not in r.body.decode()         # the PIN is never echoed or put in the cookie
    page = env.shop("/s/alpha/dashboard", cookie=cookie_from(r), **BROWSER)
    assert page.status == 200 and "Alpha Kirana" in page.body.decode() and 'id="login"' not in page.body.decode()
    data = env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r), **PAGE_FETCH)
    assert data.status == 200 and json.loads(data.body)["title"] == "Alpha Kirana"


def test_keep_me_signed_in_makes_a_thirty_day_cookie_and_session(env):
    r = env.shop("/s/alpha/dashboard/session/keep", authorization=basic("shop", "1111"))
    assert f"Max-Age={auth.REMEMBER_TTL_SEC}" in r.headers["Set-Cookie"] and auth.REMEMBER_TTL_SEC == 30 * 24 * 3600
    env.clock.now += auth.SESSION_TTL_SEC + 5
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r)).status == 200      # outlives a plain session


def test_a_plain_session_ends_after_its_time_limit(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r)).status == 200
    env.clock.now += auth.SESSION_TTL_SEC + 5
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r), **PAGE_FETCH).status == 401


def test_the_cookie_is_marked_secure_behind_https(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"), x_forwarded_proto="https")
    assert "Secure" in r.headers["Set-Cookie"]


def test_a_pin_may_use_any_characters(env):
    auth.set_pin("alpha", "पिन-९९ ü", env.tmp / "auth.json")
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "पिन-९९ ü"))
    assert r.status == 200


def test_a_wrong_pin_is_refused_and_says_how_many_tries_are_left(env):
    for left in (4, 3, 2, 1):
        r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"))
        assert r.status == 401 and json.loads(r.body) == {"ok": False, "wrong": True, "remaining": left}
        assert "Set-Cookie" not in r.headers


def test_the_fifth_wrong_pin_locks_and_the_lock_answers_with_a_wait_time(env):
    for _ in range(4):
        env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"))
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"))
    body = json.loads(r.body)
    assert r.status == 429 and body["locked"] is True and 55 <= body["retry_after"] <= 60 and r.headers["Retry-After"] == str(body["retry_after"])
    right = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    assert right.status == 429 and "Set-Cookie" not in right.headers      # even the right PIN waits
    env.clock.now += 61
    assert env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111")).status == 200


def test_a_right_pin_clears_the_wrong_guesses(env):
    for _ in range(3):
        env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"))
    env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"))
    assert json.loads(r.body)["remaining"] == 4


def test_signing_in_with_no_header_is_a_400_not_a_guess(env):
    r = env.shop("/s/alpha/dashboard/session")
    assert r.status == 400 and json.loads(r.body) == {"ok": False, "empty": True}
    assert env.throttle.remaining(("1.2.3.4", "alpha")) == 5


def test_wrong_guesses_are_counted_per_address_and_shop(env):
    for _ in range(5):
        env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"), remote="9.9.9.9")
    assert env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"), remote="9.9.9.9").status == 429
    assert env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"), remote="1.2.3.4").status == 200
    assert env.shop("/s/beta/dashboard/session", authorization=basic("shop", "2222"), remote="9.9.9.9").status == 200


def test_a_session_works_without_counting_against_the_throttle(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    for _ in range(5):
        env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "0000"), remote="1.2.3.4")
    assert not env.throttle.allowed(("1.2.3.4", "alpha"))
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r)).status == 200      # already signed in: the lock is about guessing


def test_a_new_sign_in_ends_the_old_session(env):
    first = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    second = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"), cookie=cookie_from(first))
    assert cookie_from(first) != cookie_from(second)
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(first), **PAGE_FETCH).status == 401
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(second)).status == 200


# ---- who a session lets in -------------------------------------------------

def test_a_shop_session_opens_only_that_shop(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r)).status == 200
    assert env.shop("/s/beta/dashboard/data", cookie=cookie_from(r), **PAGE_FETCH).status == 401


def test_a_shop_session_does_not_open_the_admin_page(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    assert env.adm("/admin/data", cookie=cookie_from(r), **PAGE_FETCH).status == 401
    assert env.adm("/admin/token", cookie=cookie_from(r), **PAGE_FETCH).status == 401


def test_an_admin_session_opens_any_shop_and_the_admin_page(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("admin", "admin-secret"))
    assert r.status == 200
    assert env.shop("/s/beta/dashboard/data", cookie=cookie_from(r)).status == 200
    assert env.adm("/admin/data", cookie=cookie_from(r)).status == 200


def test_the_admin_password_does_not_work_as_a_shop_pin_and_the_other_way_round(env):
    assert env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "admin-secret")).status == 401
    assert env.adm("/admin/session", authorization=basic("admin", "1111")).status == 401
    assert env.adm("/admin/session", authorization=basic("shop", "admin-secret")).status == 401     # the admin's user name is fixed


def test_a_forged_or_unknown_cookie_opens_nothing(env):
    for cookie in ("dd_session=forged", "dd_session=", "other=1", "dd_session=" + "A" * 43):
        assert env.shop("/s/alpha/dashboard/data", cookie=cookie, **PAGE_FETCH).status == 401


def test_the_pin_is_not_accepted_in_a_url(env):
    r = env.shop("/s/alpha/dashboard/data?pin=1111&password=1111", **PAGE_FETCH)
    assert r.status == 401


# ---- signing out -----------------------------------------------------------

def test_signing_out_ends_the_session_and_clears_the_cookie(env):
    r = env.shop("/s/alpha/dashboard/session", authorization=basic("shop", "1111"))
    out = env.shop("/s/alpha/dashboard/signout", cookie=cookie_from(r))
    assert out.status == 200 and "Max-Age=0" in out.headers["Set-Cookie"]
    assert env.shop("/s/alpha/dashboard/data", cookie=cookie_from(r), **PAGE_FETCH).status == 401


def test_signing_out_when_not_signed_in_is_harmless(env):
    assert env.shop("/s/alpha/dashboard/signout").status == 200
    assert env.shop("/s/alpha/dashboard/signout", cookie="dd_session=forged").status == 200


def test_signing_out_of_a_shop_does_not_depend_on_that_shop_existing_wrongly(env):
    assert env.shop("/s/nope/dashboard/signout").status == 404


# ---- the admin page --------------------------------------------------------

def test_the_admin_sign_in_page_is_for_the_admin_and_starts_dark(env):
    r = env.adm("/admin", **BROWSER)
    body = r.body.decode()
    assert r.status == 401 and "WWW-Authenticate" not in r.headers
    assert 'data-kind="admin"' in body and 'data-session="/admin/session"' in body and "DD_DEFAULT_THEME='dark'" in body


def test_the_shop_sign_in_page_follows_the_device_theme(env):
    assert "DD_DEFAULT_THEME='auto'" in env.shop("/s/alpha/dashboard", **BROWSER).body.decode()


def test_the_admin_signs_in_and_out_with_the_same_flow(env):
    r = env.adm("/admin/session", authorization=basic("admin", "admin-secret"))
    assert r.status == 200 and "HttpOnly" in r.headers["Set-Cookie"]
    assert env.adm("/admin", cookie=cookie_from(r), **BROWSER).status == 200
    assert json.loads(env.adm("/admin/token", cookie=cookie_from(r)).body)["token"]
    env.adm("/admin/signout", cookie=cookie_from(r))
    assert env.adm("/admin/data", cookie=cookie_from(r), **PAGE_FETCH).status == 401


def test_a_wrong_admin_password_counts_and_locks(env):
    for left in (4, 3, 2, 1):
        assert json.loads(env.adm("/admin/session", authorization=basic("admin", "no")).body)["remaining"] == left
    assert env.adm("/admin/session", authorization=basic("admin", "no")).status == 429
    assert env.adm("/admin/session", authorization=basic("admin", "admin-secret")).status == 429


def test_with_no_admin_password_set_the_admin_page_is_off_not_a_sign_in_page(env, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD")
    r = env.adm("/admin", **BROWSER)
    assert r.status == 503 and not r.content_type.startswith("text/html")
    assert env.adm("/admin/session", authorization=basic("admin", "anything")).status == 503


# ---- the page's own code ---------------------------------------------------

def test_the_dashboards_have_a_sign_out_button_and_the_script_that_works_it():
    for page in ("dashboard.html", "admin.html"):
        html_text = __import__("dukaan_dost.webpage", fromlist=["load"]).load(Path(__file__).resolve().parent.parent / "dukaan_dost" / "web" / page)
        assert 'id="signout"' in html_text and "/signout" in html_text


# ---- through the real server -----------------------------------------------

def test_the_cookie_travels_through_the_real_server_and_the_pin_is_not_logged(env, caplog):
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.configure(default_shop="alpha", shop_exists=lambda n: shops.exists(n, env.shops_root),
                shop_title=lambda n: shops.display_name(n, env.shops_root))
    t.add_http_handler(lambda path, headers, remote: dashboard.handle(
        path, headers, remote, shops_root=env.shops_root, orders_root=env.orders_root, throttle=env.throttle, sessions=env.sessions))
    t.start()
    try:
        def get(path, **h):
            req = urllib.request.Request(f"http://127.0.0.1:{t.port}{path}", headers={k.replace("_", "-"): v for k, v in h.items()})
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return r.status, r.headers, r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                return e.code, e.headers, e.read().decode("utf-8")

        status, headers, body = get("/s/alpha/dashboard", Accept="text/html")
        assert status == 401 and headers.get("WWW-Authenticate") is None and 'id="login"' in body
        status, headers, _ = get("/s/alpha/dashboard/session", Authorization=basic("shop", "1111"))
        assert status == 200 and "HttpOnly" in headers["Set-Cookie"] and "SameSite=Strict" in headers["Set-Cookie"]
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, _, body = get("/s/alpha/dashboard/data", Cookie=cookie)
        assert status == 200 and json.loads(body)["title"] == "Alpha Kirana"
        status, headers, _ = get("/s/alpha/dashboard/signout", Cookie=cookie)
        assert status == 200 and "Max-Age=0" in headers["Set-Cookie"]
        assert get("/s/alpha/dashboard/data", Cookie=cookie, Accept="*/*")[0] in (401,)
    finally:
        t.close()
    assert "1111" not in caplog.text
