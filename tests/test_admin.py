"""
Tests for the admin dashboard's server side (admin.py): who may open it, and what it shows.

A real server runs on a free localhost port with three shops in different states. The tests sign in the way
a browser does (HTTP Basic auth) and try the things that must not work: no password, a wrong one, a shop's
PIN, another user name, no ADMIN_PASSWORD at all, and repeated guessing.

    python -m pytest tests/test_admin.py
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import admin, auth, demo_data, shops, store  # noqa: E402
from dukaan_dost.transport_websocket import WebSocketTransport  # noqa: E402
from tests.test_shop_health import make_shop  # noqa: E402

PASSWORD = "admin-secret"


@pytest.fixture
def env(tmp_path, monkeypatch):
    shops_root, orders_root, auth_file = tmp_path / "shops", tmp_path / "orders", tmp_path / "auth.json"
    shops_root.mkdir()
    make_shop(shops_root, "alpha", config='system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "Alpha Kirana"\n')
    make_shop(shops_root, "beta", config=None, core=False, topics=[], stock=None)     # broken: no config, no knowledge, no stock
    make_shop(shops_root, "gamma")                                                      # fine, but no PIN
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)
    auth.set_pin("alpha", "1111", auth_file)
    auth.set_pin("beta", "2222", auth_file)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    demo_data.seed("alpha", orders_root, now=datetime.now(store.IST))

    calls = [{"shop": "alpha", "seconds": 42}]
    throttle = auth.Throttle(max_failures=5, lock_sec=60)
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.configure(default_shop="alpha", shop_exists=lambda n: shops.exists(n, shops_root),
                shop_title=lambda n: shops.display_name(n, shops_root))
    t.add_http_handler(lambda path, headers, remote: admin.handle(
        path, headers, remote, shops_root=shops_root, orders_root=orders_root, throttle=throttle,
        live_calls=lambda: calls, auth_path=auth_file))
    t.start()
    yield t
    t.close()


def get(t, path, user="admin", password=None):
    req = urllib.request.Request(f"http://127.0.0.1:{t.port}{path}")
    if password is not None:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


def data(t):
    status, _, body = get(t, "/admin/data", password=PASSWORD)
    assert status == 200
    return json.loads(body)


# ---- who may open it --------------------------------------------------------

@pytest.mark.parametrize("path", ["/admin", "/admin/", "/admin/data", "/admin/data/"])
def test_no_credentials_gets_a_sign_in_prompt(env, path):
    status, headers, _ = get(env, path)
    assert status == 401 and headers["WWW-Authenticate"].startswith("Basic ")


@pytest.mark.parametrize("path", ["/admin", "/admin/data"])
def test_the_admin_password_opens_the_admin_routes(env, path):
    assert get(env, path, password=PASSWORD)[0] == 200


@pytest.mark.parametrize("password", ["wrong", "", " " + PASSWORD, PASSWORD + " ", PASSWORD.upper()])
def test_a_wrong_admin_password_is_refused(env, password):
    assert get(env, "/admin/data", password=password)[0] == 401


@pytest.mark.parametrize("pin", ["1111", "2222"])
def test_a_shops_pin_does_not_open_the_admin_page(env, pin):
    """The admin page shows every shop; a shopkeeper's PIN must never reach it, whatever user name is used."""
    for user in ("admin", "alpha", "beta"):
        assert get(env, "/admin/data", user=user, password=pin)[0] == 401


@pytest.mark.parametrize("user", ["alpha", "root", "Admin", ""])
def test_the_admin_password_only_works_for_the_user_admin(env, user):
    assert get(env, "/admin/data", user=user, password=PASSWORD)[0] == 401


def test_with_no_admin_password_set_the_page_is_off_not_open(env, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD")
    for password in (None, "", PASSWORD, "anything"):
        status, _, body = get(env, "/admin/data", password=password)
        assert status == 503 and "ADMIN_PASSWORD" in body


def test_the_example_placeholder_password_counts_as_not_set(env, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "your-admin-password-here")
    status, _, _ = get(env, "/admin/data", password="your-admin-password-here")
    assert status == 503


def test_repeated_wrong_guesses_lock_the_address_out_even_for_the_right_password(env):
    for _ in range(5):
        assert get(env, "/admin/data", password="nope")[0] == 401
    status, headers, _ = get(env, "/admin/data", password=PASSWORD)
    assert status == 429 and headers["Retry-After"] == "60"


def test_a_good_sign_in_resets_the_failure_count(env):
    for _ in range(4):
        get(env, "/admin/data", password="nope")
    assert get(env, "/admin/data", password=PASSWORD)[0] == 200
    for _ in range(4):
        get(env, "/admin/data", password="nope")
    assert get(env, "/admin/data", password=PASSWORD)[0] == 200


def test_other_paths_are_not_taken_over(env):
    for path in ("/admin/other", "/administrator", "/admin/data/x", "/s/alpha/admin"):
        assert get(env, path, password=PASSWORD)[0] == 404


def test_responses_carry_the_strict_security_headers(env):
    for path in ("/admin", "/admin/data"):
        _, headers, _ = get(env, path, password=PASSWORD)
        assert headers["Cache-Control"] == "no-store"
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert headers["X-Frame-Options"] == "DENY"


# ---- what it shows ----------------------------------------------------------

def test_every_shop_is_listed_with_its_state(env):
    d = data(env)
    by_name = {s["name"]: s for s in d["shops"]}
    assert set(by_name) == {"alpha", "beta", "gamma"}
    assert by_name["alpha"]["state"] == "ready"
    assert by_name["beta"]["state"] == "broken"            # no config: an error
    assert by_name["gamma"]["state"] == "attention"        # works, but has no PIN
    assert by_name["alpha"]["title"] == "Alpha Kirana"


def test_pin_and_live_call_are_reported_per_shop(env):
    by_name = {s["name"]: s for s in data(env)["shops"]}
    assert by_name["alpha"]["has_pin"] and by_name["beta"]["has_pin"] and not by_name["gamma"]["has_pin"]
    assert by_name["alpha"]["live"] == [42] and by_name["beta"]["live"] == []


def test_a_shop_with_orders_shows_them_and_a_shop_without_shows_zeros_and_no_date(env):
    by_name = {s["name"]: s for s in data(env)["shops"]}
    assert by_name["alpha"]["orders_total"] > 0 and by_name["alpha"]["last_order"]
    assert by_name["gamma"]["orders_total"] == 0 and by_name["gamma"]["orders_today"] == 0
    assert by_name["gamma"]["last_order"] is None           # no invented date


def test_the_totals_add_up_the_shops(env):
    d = data(env)
    shops_ = d["shops"]
    t = d["totals"]
    assert t["shops"] == 3 and t["shops_ready"] == 1 and t["shops_attention"] == 1 and t["shops_broken"] == 1
    assert t["orders_today"] == sum(s["orders_today"] for s in shops_)
    assert t["live_calls"] == 1
    assert t["errors"] + t["warnings"] == len(d["problems"])
    assert sum(s["problems"] for s in shops_) == len(d["problems"])


def test_problems_are_listed_errors_first_with_the_fields_a_page_needs(env):
    problems = data(env)["problems"]
    assert problems, "beta and gamma should have problems"
    severities = [p["severity"] for p in problems]
    assert severities == sorted(severities, key=lambda s: {"error": 0, "warning": 1}[s])
    assert all(set(p) == {"id", "shop", "severity", "title", "detail"} for p in problems)
    assert any(p["id"] == "gamma:no-pin" for p in problems)
    assert not any(p["shop"] == "alpha" for p in problems)


def test_nothing_about_a_call_but_its_length_is_shared(env):
    body = get(env, "/admin/data", password=PASSWORD)[2]
    assert '"live": [42]' in body and "seconds" not in body


def test_a_shop_name_with_markup_travels_as_data_not_as_page(env, tmp_path):
    """The page builds everything from text nodes (checked in the page tests); the server only has to keep it as data."""
    shops_root = tmp_path / "shops"
    (shops_root / "delta").mkdir()
    (shops_root / "delta" / "config.yaml").write_text(
        'system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "<img src=x onerror=alert(1)>"\n', encoding="utf-8")
    delta = [s for s in data(env)["shops"] if s["name"] == "delta"][0]
    assert delta["title"] == "<img src=x onerror=alert(1)>"


def test_an_empty_install_gives_an_empty_overview(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    d = admin.snapshot(tmp_path / "no-shops", tmp_path / "no-orders", None, auth_path=tmp_path / "auth.json")
    assert d["shops"] == [] and d["problems"] == []
    assert d["totals"]["shops"] == 0 and d["totals"]["orders_today"] == 0 and d["solved"] == []


def test_a_live_call_source_that_fails_does_not_break_the_overview(tmp_path, monkeypatch):
    shops_root = tmp_path / "shops"
    shops_root.mkdir()
    make_shop(shops_root, "alpha")
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")

    def broken():
        raise RuntimeError("transport gone")

    d = admin.snapshot(shops_root, tmp_path / "orders", broken, auth_path=tmp_path / "auth.json")
    assert d["shops"][0]["live"] == []


def test_money_is_not_part_of_the_admin_overview(env):
    """Sales and credit are the shopkeeper's business; the admin page is about whether the system works."""
    d = data(env)
    body = json.dumps(d)
    for field in ("sales_today", "udhaar_outstanding"):
        assert field not in body
