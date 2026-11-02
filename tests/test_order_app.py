"""
Tests for the order's life inside the main program: a new order when a call starts, the order file
written when it ends, and nothing breaking if saving fails.

    python -m pytest tests/test_order_app.py
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import store  # noqa: E402


@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


@pytest.fixture(autouse=True)
def isolated(app, monkeypatch, tmp_path):
    monkeypatch.setattr(store, "ORDERS_DIR", tmp_path)
    app._finish_order("test setup")
    app._clear_history("test setup")
    yield
    app._finish_order("test teardown")


def sugar(qty):
    return [{"op": "add", "sku": "SUGAR-1KG", "qty": qty}]


def test_a_call_starting_gives_the_shop_an_empty_order(app):
    app._set_active_shop()
    assert app._order is not None and app._order.shop == "dukaan_dost" and app._order.is_empty


def test_the_order_is_written_when_the_call_ends(app, tmp_path):
    app._set_active_shop()
    app._order.apply(sugar(2), payment="cash", customer="Ramesh")
    app._clear_history("call ended")
    saved = json.loads((tmp_path / "dukaan_dost" / f"order_{_only_call_id(tmp_path)}.json").read_text(encoding="utf-8"))
    assert saved["total"] == 88 and saved["status"] == "confirmed" and saved["customer"] == "Ramesh"
    assert app._order is None


def _only_call_id(root):
    files = list((root / "dukaan_dost").glob("order_*.json"))
    assert len(files) == 1, files
    return files[0].stem[len("order_"):]


def test_a_call_that_ordered_nothing_writes_no_file(app, tmp_path):
    app._set_active_shop()
    app._clear_history("call ended")
    assert not (tmp_path / "dukaan_dost").exists() and app._order is None


def test_an_order_left_open_is_saved_when_the_next_call_starts(app, tmp_path):
    app._set_active_shop()
    app._order.apply(sugar(1))
    first = app._order
    app._clear_history("new call")                    # what the watchdog does before it starts the next call
    app._set_active_shop()
    assert app._order is not first and app._order.is_empty
    assert len(list((tmp_path / "dukaan_dost").glob("order_*.json"))) == 1


def test_the_page_listener_is_the_transports_event_sender(app):
    app._set_active_shop()
    assert app._order.listener == app._transport.send_event


def test_a_shop_without_a_stock_list_gets_no_order(app, monkeypatch):
    class Plain:
        stock_items = []
    monkeypatch.setattr(app, "_get_conv_mgr", lambda shop=None: Plain())
    app._start_order("whatever")
    assert app._order is None


def test_a_failure_while_saving_does_not_break_the_call(app, monkeypatch):
    app._set_active_shop()
    app._order.apply(sugar(1))

    def boom(self, root=None):
        raise OSError("disk full")
    monkeypatch.setattr(type(app._order), "close", boom)
    app._clear_history("call ended")                  # must not raise
    assert app._order is None


def test_finishing_with_no_order_is_harmless(app):
    app._finish_order("nothing to finish")
    app._finish_order("still nothing")


def test_the_reply_path_hands_the_current_order_to_the_conversation_manager(app, monkeypatch):
    seen = {}

    class Fake:
        def handle_turn_streaming(self, transcript, recent, context, language_code, order=None):
            seen["order"] = order
            yield "ok.", language_code

    monkeypatch.setattr(app, "_get_conv_mgr", lambda shop=None: Fake())
    app._set_active_shop()
    # _set_active_shop used the Fake too, so build the order by hand
    app._order = None
    from dukaan_dost.order_session import OrderSession
    app._order = OrderSession("dukaan_dost", [], now=None)
    list(app._ask_streaming("hello", "en-IN"))
    assert seen["order"] is app._order
