"""
Tests for the live view of a call in progress (live_feed.py and what carries it to the signed-in dashboard).

The feed holds the conversation, the order so far and the loan quote of the call that is happening, in memory only, so a
phone call can be watched on the shopkeeper's dashboard. The things that must hold: it follows one call at a time, it
disappears with the call, it never reaches anyone who is not signed in, it survives odd events, and a phone provider's
socket still receives nothing.

    python -m pytest tests/test_live_feed.py
"""

import json
import sys
import time
import urllib.request
import base64
from pathlib import Path

import pytest
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import auth, dashboard, live_feed, shops  # noqa: E402
from dukaan_dost.live_feed import LiveFeed, MAX_LINES, MAX_TEXT  # noqa: E402
from dukaan_dost.transport_websocket import WebSocketTransport  # noqa: E402

ORDER = {"type": "order", "total": 285, "items": [{"name": "Rice", "qty": 2, "unit": "kg", "line_total": 120},
                                                   {"name": "Sunflower oil", "qty": 1, "unit": "litre", "line_total": 165}]}


# ---- the feed ----------------------------------------------------------------------------------------------------

def test_the_conversation_the_order_and_the_language_are_kept_in_order():
    f = LiveFeed()
    f.add("c1", {"type": "user", "text": "do kilo chawal", "lang": "hi-IN"})
    f.add("c1", {"type": "agent", "reply": 1, "text": "Theek hai."})
    f.add("c1", ORDER)
    f.add("c1", {"type": "user", "text": "bas itna"})
    v = f.view("c1")
    assert [(x["who"], x["text"]) for x in v["lines"]] == [("caller", "do kilo chawal"), ("agent", "Theek hai."), ("caller", "bas itna")]
    assert v["language"] == "hi-IN"
    assert v["order"]["total"] == 285 and [i["name"] for i in v["order"]["items"]] == ["Rice", "Sunflower oil"]
    assert v["loan"] is None


def test_the_pieces_of_one_agent_reply_join_into_one_line_and_a_new_reply_starts_a_new_one():
    f = LiveFeed()
    f.add("c1", {"type": "agent", "reply": 5, "text": "Do kilo chawal."})
    f.add("c1", {"type": "agent", "reply": 5, "text": "Total 120 rupaye."})
    f.add("c1", {"type": "agent", "reply": 6, "text": "Aur kuch?"})
    assert [x["text"] for x in f.view("c1")["lines"]] == ["Do kilo chawal. Total 120 rupaye.", "Aur kuch?"]


def test_a_caller_line_between_two_replies_keeps_them_apart():
    f = LiveFeed()
    f.add("c1", {"type": "agent", "reply": 1, "text": "Hello."})
    f.add("c1", {"type": "user", "text": "ek kilo daal"})
    f.add("c1", {"type": "agent", "reply": 1, "text": "Still the same id."})       # a reply id seen again after the caller spoke
    assert [x["who"] for x in f.view("c1")["lines"]] == ["agent", "caller", "agent"]


def test_the_loan_quote_is_kept_without_its_type():
    f = LiveFeed()
    f.add("c1", {"type": "loan", "heard_amount": 100000, "kind": "margin_money", "loan_amount": 700000, "monthly_instalment": 15000, "business": "kirana", "place": "Nandyal"})
    loan = f.view("c1")["loan"]
    assert "type" not in loan and loan["loan_amount"] == 700000 and loan["place"] == "Nandyal"


def test_the_feed_follows_one_call_and_a_new_call_starts_clean():
    f = LiveFeed()
    f.add("c1", {"type": "user", "text": "first call", "lang": "te-IN"})
    f.add("c1", ORDER)
    f.add("c2", {"type": "user", "text": "second call"})
    assert f.view("c1") == {"language": None, "lines": [], "order": None, "loan": None}     # the first call is gone
    v = f.view("c2")
    assert [x["text"] for x in v["lines"]] == ["second call"] and v["order"] is None and v["language"] is None


def test_a_call_nothing_was_said_in_has_an_empty_feed():
    f = LiveFeed()
    assert f.view("nobody") == {"language": None, "lines": [], "order": None, "loan": None}
    f.clear()
    assert f.view(None)["lines"] == []


def test_clear_forgets_everything():
    f = LiveFeed()
    f.add("c1", {"type": "user", "text": "secret words"})
    f.clear()
    assert f.view("c1")["lines"] == []


def test_only_the_last_lines_are_kept_and_a_long_line_is_cut():
    f = LiveFeed()
    for n in range(MAX_LINES + 25):
        f.add("c1", {"type": "user", "text": f"line {n}"})
    lines = f.view("c1")["lines"]
    assert len(lines) == MAX_LINES and lines[-1]["text"] == f"line {MAX_LINES + 24}" and lines[0]["text"] == "line 25"
    f.add("c1", {"type": "user", "text": "x" * (MAX_TEXT * 3)})
    assert len(f.view("c1")["lines"][-1]["text"]) == MAX_TEXT


@pytest.mark.parametrize("event", [None, 5, "text", [], {}, {"type": "user"}, {"type": "user", "text": None}, {"type": "agent", "text": "   "},
                                   {"type": "order", "items": "not a list"}, {"type": "order", "total": "lots", "items": [1, None, {"name": "ok"}]},
                                   {"type": "loan", "nested": {"a": 1}, "list": [1]}, {"type": "something else", "text": "ignored"}])
def test_odd_events_never_raise_and_leave_a_usable_feed(event):
    f = LiveFeed()
    f.add("c1", event)
    v = f.view("c1")
    json.dumps(v)                                             # whatever is kept can be sent to a page
    assert isinstance(v["lines"], list)


def test_what_is_kept_is_plain_json_only():
    f = LiveFeed()
    f.add("c1", {"type": "order", "total": 10, "items": [{"name": "Rice", "qty": 1, "unit": "kg", "line_total": 10, "obj": object(), "nested": {"a": 1}}]})
    item = f.view("c1")["order"]["items"][0]
    assert set(item) == {"name", "qty", "unit", "line_total"}


def test_a_view_is_a_copy_so_the_reader_cannot_change_the_feed():
    f = LiveFeed()
    f.add("c1", {"type": "user", "text": "hello"})
    f.view("c1")["lines"].append({"who": "caller", "text": "injected"})
    assert len(f.view("c1")["lines"]) == 1


def test_the_feed_is_never_written_anywhere():
    source = Path(live_feed.__file__).read_text(encoding="utf-8")
    for banned in ("open(", "write_text", "json.dump(", "logging", "log.", "print(", "sqlite", "pickle"):
        assert banned not in source, banned


# ---- the transports ----------------------------------------------------------------------------------------------

@pytest.fixture
def server():
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.configure(default_shop="alpha", shop_exists=lambda n: n == "alpha", shop_title=lambda n: "Alpha Kirana")
    t.start()
    yield t
    t.close()


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_a_browser_call_shows_its_conversation_in_live_calls_and_still_reaches_the_page(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        assert json.loads(ws.recv(timeout=3))["type"] == "ready"
        assert wait_for(lambda: server.find_call()[0] is not None)
        server.send_event({"type": "user", "text": "ek kilo chawal", "lang": "hi-IN"})
        server.send_event({"type": "agent", "reply": 1, "text": "Theek hai."})
        server.send_event(ORDER)
        assert json.loads(ws.recv(timeout=3))["text"] == "ek kilo chawal"        # the page still gets its events
        live = server.live_calls()
        assert len(live) == 1 and live[0]["shop"] == "alpha" and live[0]["channel"] == "browser"
        assert [x["text"] for x in live[0]["lines"]] == ["ek kilo chawal", "Theek hai."]
        assert live[0]["order"]["total"] == 285 and live[0]["language"] == "hi-IN"


def test_when_the_call_ends_what_was_said_goes_with_it(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
        server.send_event({"type": "user", "text": "private words", "lang": "en-IN"})
        assert server.live_calls()[0]["lines"]
    assert wait_for(lambda: server.find_call()[0] is None)
    assert server.live_calls() == []
    assert server._feed.view("anything")["lines"] == [] and server._feed._lines == []      # cleared, not merely hidden


def test_the_next_call_does_not_inherit_the_last_ones_words(server):
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
        server.send_event({"type": "user", "text": "first caller", "lang": "en-IN"})
    assert wait_for(lambda: server.find_call()[0] is None)
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=3)
        assert wait_for(lambda: server.find_call()[0] is not None)
        live = server.live_calls()
        assert live and live[0]["lines"] == [] and live[0]["order"] is None


def test_an_event_with_no_call_is_not_kept(server):
    server.send_event({"type": "user", "text": "nobody is listening"})
    assert server._feed._lines == []


# ---- what the dashboard sends, and to whom -------------------------------------------------------------------------

@pytest.fixture
def dash(tmp_path, monkeypatch):
    shops_root, orders_root = tmp_path / "shops", tmp_path / "orders"
    for name in ("alpha", "beta"):
        (shops_root / name).mkdir(parents=True)
        (shops_root / name / "config.yaml").write_text(f'system_prompt: "x"\nfallback_messages:\n  en-in: "y"\ndisplay_name: "{name}"\n', encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)
    auth.set_pin("alpha", "1111", auth_file)
    auth.set_pin("beta", "2222", auth_file)
    live = [{"shop": "alpha", "seconds": 42, "channel": "phone", "language": "hi-IN",
             "lines": [{"who": "caller", "text": "do kilo chawal"}], "order": {"total": 120, "items": []}, "loan": None},
            {"shop": "beta", "seconds": 7, "channel": "phone", "language": "te-IN", "lines": [{"who": "caller", "text": "beta's private words"}], "order": None, "loan": None}]
    throttle = auth.Throttle(max_failures=5, lock_sec=60)
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.configure(default_shop="alpha", shop_exists=lambda n: shops.exists(n, shops_root), shop_title=lambda n: n)
    t.add_http_handler(lambda path, headers, remote: dashboard.handle(path, headers, remote, shops_root=shops_root, orders_root=orders_root,
                                                                      throttle=throttle, live_calls=lambda: live))
    t.start()
    yield t
    t.close()


def get(t, path, user=None, password=None):
    import urllib.error
    req = urllib.request.Request(f"http://127.0.0.1:{t.port}{path}")
    if password is not None:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user or 'shop'}:{password}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def test_the_signed_in_shopkeeper_sees_the_conversation_of_the_live_call(dash):
    status, body = get(dash, "/s/alpha/dashboard/data", "shop", "1111")
    live = json.loads(body)["live"]
    assert status == 200 and len(live) == 1
    assert live[0]["seconds"] == 42 and live[0]["channel"] == "phone" and live[0]["language"] == "hi-IN"
    assert live[0]["lines"] == [{"who": "caller", "text": "do kilo chawal"}] and live[0]["order"]["total"] == 120 and live[0]["loan"] is None


def test_another_shops_call_is_never_in_this_shops_data(dash):
    _, body = get(dash, "/s/alpha/dashboard/data", "shop", "1111")
    assert "beta's private words" not in body and "te-IN" not in body


@pytest.mark.parametrize("creds", [(None, None), ("shop", "wrong"), ("shop", "2222")])
def test_nobody_else_gets_the_words_of_a_call(dash, creds):
    status, body = get(dash, "/s/alpha/dashboard/data", *creds)
    assert status in (401, 429) and "do kilo chawal" not in body


def test_the_dashboard_page_itself_carries_no_conversation(dash):
    status, body = get(dash, "/s/alpha/dashboard", "shop", "1111")
    assert status == 200 and "do kilo chawal" not in body


def test_a_transport_that_keeps_no_feed_still_gives_the_length_of_the_call():
    live = dashboard._live_for("alpha", lambda: [{"shop": "alpha", "seconds": 9}])
    assert live == [{"seconds": 9, "channel": "browser", "language": None, "lines": [], "order": None, "loan": None}]


def test_a_failing_live_source_gives_an_empty_list_not_an_error():
    def boom():
        raise RuntimeError("transport busy")
    assert dashboard._live_for("alpha", boom) == []
