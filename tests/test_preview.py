"""
Tests for the keyless dashboard preview (python -m dukaan_dost.preview).

    python -m pytest tests/test_preview.py
"""

import base64
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import auth, preview  # noqa: E402


@pytest.fixture
def running(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_FILE", auth.AUTH_FILE)       # restored afterwards
    transport, tmp = preview.build(port=0)
    yield transport, tmp
    transport.close()
    shutil.rmtree(tmp, ignore_errors=True)


def get(transport, path, pin=None):
    req = urllib.request.Request(f"http://127.0.0.1:{transport.port}{path}")
    if pin is not None:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"shop:{pin}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, ""


def test_the_preview_serves_a_dashboard_full_of_demo_data(running):
    transport, _ = running
    status, body = get(transport, f"/s/{preview.SHOP}/dashboard/data", preview.PIN)
    data = json.loads(body)
    assert status == 200 and data["title"] == preview.TITLE
    assert data["orders"] and data["ledger"] and data["loans"]
    assert all(o["synthetic"] for o in data["orders"])


def test_the_preview_still_asks_for_the_pin(running):
    transport, _ = running
    assert get(transport, f"/s/{preview.SHOP}/dashboard")[0] == 401
    assert get(transport, f"/s/{preview.SHOP}/dashboard/data", "0000")[0] == 401


def test_the_preview_never_touches_the_real_folders(running):
    _, tmp = running
    repo = Path(__file__).resolve().parent.parent
    assert repo not in tmp.parents
    assert not (repo / "orders" / preview.SHOP).exists()
    assert not (repo / "shops" / preview.SHOP).exists()


def test_the_preview_page_is_served(running):
    transport, _ = running
    status, body = get(transport, f"/s/{preview.SHOP}/dashboard", preview.PIN)
    assert status == 200 and "Demo Kirana" in body


def test_the_data_includes_live_calls_for_this_shop_only(running):
    transport, _ = running
    transport.add_http_handler(lambda p, h, r: None)       # no effect; keeps the handler list non-empty
    from dukaan_dost import dashboard
    calls = lambda: [{"shop": preview.SHOP, "seconds": 12, "who": "secret"}, {"shop": "other", "seconds": 99}]
    headers = {"Authorization": "Basic " + base64.b64encode(f"shop:{preview.PIN}".encode()).decode()}
    reply = dashboard.handle(f"/s/{preview.SHOP}/dashboard/data", headers, "t",
                             shops_root=Path(running[1]) / "shops", orders_root=Path(running[1]) / "orders",
                             live_calls=calls)
    assert json.loads(reply.body)["live"] == [{"seconds": 12}]


def test_a_failing_call_source_does_not_break_the_dashboard():
    from dukaan_dost import dashboard
    def boom():
        raise RuntimeError("x")
    assert dashboard._live_for("a", boom) == [] and dashboard._live_for("a", None) == []
