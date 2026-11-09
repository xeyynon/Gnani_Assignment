"""
Tests for the shopkeeper dashboard's server side and the call-link routing (DEC-034).

A real server runs on a free localhost port with two shops. The tests sign in the way a
browser does (HTTP Basic auth) and try the things that must not work: no PIN, a wrong PIN,
another shop's PIN, repeated guessing, odd shop names, and markup smuggled in through an
order's customer name.

    python -m pytest tests/test_dashboard.py
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest
from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import auth, dashboard, demo_data, shops, store  # noqa: E402
from dukaan_dost.transport_websocket import WebSocketTransport  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    shops_root = tmp_path / "shops"
    orders_root = tmp_path / "orders"
    for name, display in [("alpha", "Alpha Kirana"), ("beta", "Beta Store")]:
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

    throttle = auth.Throttle(max_failures=5, lock_sec=60)
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.configure(default_shop="alpha", shop_exists=lambda n: shops.exists(n, shops_root),
                shop_title=lambda n: shops.display_name(n, shops_root))
    t.add_http_handler(lambda path, headers, remote: dashboard.handle(
        path, headers, remote, shops_root=shops_root, orders_root=orders_root, throttle=throttle))
    t.start()
    yield t, shops_root, orders_root
    t.close()


def get(t, path, user=None, password=None):
    req = urllib.request.Request(f"http://127.0.0.1:{t.port}{path}")
    if password is not None:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user or 'shop'}:{password}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


# ---- sign-in ---------------------------------------------------------------

def test_no_credentials_gets_a_sign_in_prompt(env):
    status, headers, _ = get(env[0], "/s/alpha/dashboard")
    assert status == 401 and headers["WWW-Authenticate"].startswith("Basic ")


@pytest.mark.parametrize("path", ["/s/alpha/dashboard", "/s/alpha/dashboard/data", "/s/alpha/dashboard/"])
def test_the_right_pin_opens_every_dashboard_route(env, path):
    assert get(env[0], path, password="1111")[0] == 200


@pytest.mark.parametrize("pin", ["1112", "", "2222", "admin-secret", " 1111"])
def test_a_wrong_pin_is_refused(env, pin):
    assert get(env[0], "/s/alpha/dashboard/data", password=pin)[0] == 401


def test_another_shops_pin_does_not_open_this_shop(env):
    t = env[0]
    assert get(t, "/s/beta/dashboard/data", password="2222")[0] == 200
    assert get(t, "/s/alpha/dashboard/data", password="2222")[0] == 401


def test_a_shop_with_no_pin_cannot_be_opened(env, monkeypatch):
    t, shops_root, _ = env
    folder = shops_root / "gamma"
    folder.mkdir()
    (folder / "config.yaml").write_text('system_prompt: "x"\nfallback_messages:\n  en-in: "y"\n', encoding="utf-8")
    for pin in ("", "0000", "1111"):
        assert get(t, "/s/gamma/dashboard/data", password=pin)[0] == 401


def test_the_admin_password_opens_any_shop_only_as_admin(env):
    t = env[0]
    assert get(t, "/s/alpha/dashboard/data", user="admin", password="admin-secret")[0] == 200
    assert get(t, "/s/beta/dashboard/data", user="admin", password="admin-secret")[0] == 200
    assert get(t, "/s/alpha/dashboard/data", user="shop", password="admin-secret")[0] == 401
    assert get(t, "/s/alpha/dashboard/data", user="admin", password="wrong")[0] == 401


def test_repeated_wrong_guesses_lock_that_shop(env):
    t = env[0]
    for _ in range(5):
        assert get(t, "/s/alpha/dashboard/data", password="0000")[0] == 401
    status, headers, _ = get(t, "/s/alpha/dashboard/data", password="1111")     # even the right PIN waits
    assert status == 429 and headers["Retry-After"] == "60"
    assert get(t, "/s/beta/dashboard/data", password="2222")[0] == 200          # other shops unaffected


@pytest.mark.parametrize("path", [
    "/s/nope/dashboard", "/s/ALPHA/dashboard", "/s/..%2f..%2fetc/dashboard", "/s/../dashboard",
    "/s/alpha%2f..%2fbeta/dashboard", "/s/a/dashboard", "/s//dashboard",
])
def test_unknown_or_odd_shop_names_are_404(env, path):
    assert get(env[0], path, password="1111")[0] == 404


# ---- what the dashboard serves ---------------------------------------------

def test_the_page_is_html_with_a_locked_down_policy_and_the_escaped_shop_name(env):
    t, shops_root, _ = env
    (shops_root / "alpha" / "config.yaml").write_text(
        'system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "<script>alert(1)</script>"\n', encoding="utf-8")
    status, headers, body = get(t, "/s/alpha/dashboard", password="1111")
    assert status == 200 and headers.get_all("Content-Type") == ["text/html; charset=utf-8"]
    assert "<script>alert(1)</script>" not in body and "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "no-store" in headers["Cache-Control"] and headers["X-Frame-Options"] == "DENY"


def test_the_data_is_json_with_the_expected_shape(env):
    status, headers, body = get(env[0], "/s/alpha/dashboard/data", password="1111")
    data = json.loads(body)
    assert status == 200 and headers["Content-Type"].startswith("application/json")
    assert data["shop"] == "alpha" and data["title"] == "Alpha Kirana"
    assert set(data) >= {"summary", "orders", "loans", "ledger", "problems", "generated_at"}
    assert data["summary"]["orders_today"] > 0 and data["orders"] and data["ledger"] and data["loans"]


def test_a_shop_only_sees_its_own_data(env):
    data = json.loads(get(env[0], "/s/beta/dashboard/data", password="2222")[2])
    assert data["orders"] == [] and data["ledger"] == [] and data["summary"]["orders_total"] == 0


def test_a_new_order_shows_up_on_the_next_poll(env):
    t, _, orders_root = env
    before = json.loads(get(t, "/s/beta/dashboard/data", password="2222")[2])["summary"]["orders_total"]
    store.write_order("beta", {"call_id": "live1", "time": datetime.now(store.IST).isoformat(), "status": "confirmed",
                               "customer": None, "items": [], "total": 40, "payment": "cash"}, orders_root)
    after = json.loads(get(t, "/s/beta/dashboard/data", password="2222")[2])
    assert after["summary"]["orders_total"] == before + 1 and after["orders"][0]["id"] == "live1"


def test_markup_in_order_data_is_data_not_html(env):
    t, _, orders_root = env
    evil = '<img src=x onerror=alert(1)>'
    store.write_order("alpha", {"call_id": "evil", "time": datetime.now(store.IST).isoformat(), "status": "confirmed",
                                "customer": evil, "items": [{"name": evil, "qty": 1, "unit": "x", "line_total": 1}],
                                "total": 1, "payment": "cash"}, orders_root)
    _, _, body = get(t, "/s/alpha/dashboard/data", password="1111")
    assert json.loads(body)["orders"][0]["customer"] == evil          # carried as plain data
    page = get(t, "/s/alpha/dashboard", password="1111")[2]
    assert "innerHTML" not in page and "outerHTML" not in page and "document.write" not in page
    assert evil not in page


# ---- call links ------------------------------------------------------------

def test_each_shops_call_page_carries_its_own_name(env):
    t = env[0]
    assert "Alpha Kirana" in get(t, "/s/alpha/")[2]
    assert "Beta Store" in get(t, "/s/beta")[2]
    assert "Alpha Kirana" in get(t, "/")[2]                           # the default shop
    assert get(t, "/s/nope/")[0] == 404 and get(t, "/s/Bad%20Name/")[0] == 404


def test_a_call_on_a_shops_link_is_for_that_shop(env):
    t = env[0]
    with connect(f"ws://127.0.0.1:{t.port}/s/beta/ws") as ws:
        assert json.loads(ws.recv(timeout=3))["type"] == "ready"
        import time
        for _ in range(50):
            if t.call_shop():
                break
            time.sleep(0.05)
        assert t.call_shop() == "beta"


def test_the_plain_link_calls_the_default_shop(env):
    t = env[0]
    with connect(f"ws://127.0.0.1:{t.port}/ws") as ws:
        ws.recv(timeout=3)
        import time
        for _ in range(50):
            if t.call_shop():
                break
            time.sleep(0.05)
        assert t.call_shop() == "alpha"


def test_a_call_to_an_unknown_shop_is_refused(env):
    with pytest.raises(InvalidStatus) as err:
        with connect(f"ws://127.0.0.1:{env[0].port}/s/nope/ws"):
            pass
    assert err.value.response.status_code == 404


def test_the_operator_is_told_where_to_call_and_where_the_dashboard_is(env):
    text = env[0].describe()
    assert "/s/alpha/" in text and "/s/alpha/dashboard" in text


# ---- the full-screen Live call page (/s/<shop>/live) -------------------------

def test_the_live_page_asks_for_the_same_sign_in(env):
    status, headers, _ = get(env[0], "/s/alpha/live")
    assert status == 401 and headers["WWW-Authenticate"].startswith("Basic ")


def test_the_live_page_opens_for_this_shops_pin_only(env):
    t = env[0]
    assert get(t, "/s/alpha/live", password="1111")[0] == 200
    assert get(t, "/s/alpha/live/", password="1111")[0] == 200
    assert get(t, "/s/alpha/live", password="2222")[0] == 401           # another shop's PIN
    assert get(t, "/s/alpha/live", password="1112")[0] == 401           # a wrong PIN
    assert get(t, "/s/nobody/live", password="1111")[0] == 404          # a shop that does not exist


def test_the_live_page_is_html_with_the_locked_down_policy_and_the_escaped_shop_name(env):
    t, shops_root, _ = env
    (shops_root / "alpha" / "config.yaml").write_text(
        'system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "<script>alert(1)</script>"\n', encoding="utf-8")
    status, headers, body = get(t, "/s/alpha/live", password="1111")
    assert status == 200 and headers.get_all("Content-Type") == ["text/html; charset=utf-8"]
    assert "<script>alert(1)</script>" not in body and "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "no-store" in headers["Cache-Control"] and headers["X-Frame-Options"] == "DENY"
    assert "live call" in body                                          # it is the Live page, not the dashboard


def test_the_live_page_and_the_dashboard_are_different_pages(env):
    t = env[0]
    assert get(t, "/s/alpha/live", password="1111")[2] != get(t, "/s/alpha/dashboard", password="1111")[2]
