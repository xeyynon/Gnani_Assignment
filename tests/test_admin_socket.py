"""
Tests for the admin dashboard's command socket: how a page gets the right to send commands, who is turned away,
and that each command works end to end through a real server and a real WebSocket client.

    python -m pytest tests/test_admin_socket.py
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import admin, auth, shops  # noqa: E402
from dukaan_dost.transport_websocket import WebSocketTransport  # noqa: E402
from tests.test_admin_actions import stocked_shop  # noqa: E402

PASSWORD = "admin-secret"


class Changes(list):
    """Records which shops the agent was told about; can be made to fail like a broken agent hook."""
    fail = False

    def append(self, shop):
        if self.fail:
            raise RuntimeError("agent hook broke")
        super().append(shop)


@pytest.fixture
def env(tmp_path, monkeypatch):
    shops_root, orders_root = tmp_path / "shops", tmp_path / "orders"
    auth_file, state = tmp_path / "auth.json", tmp_path / "state.json"
    shops_root.mkdir()
    stocked_shop(shops_root, "alpha")
    monkeypatch.setattr(auth, "AUTH_FILE", auth_file)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    changed = Changes()
    tokens = admin.TokenStore()
    log_file = tmp_path / "log.jsonl"
    kw = dict(shops_root=shops_root, orders_root=orders_root, auth_path=auth_file, state_path=state, log_path=log_file)
    t = WebSocketTransport(host="127.0.0.1", port=0)
    t.configure(default_shop="alpha", shop_exists=lambda n: shops.exists(n, shops_root))
    t.add_http_handler(lambda path, headers, remote: admin.handle(
        path, headers, remote, throttle=auth.Throttle(5, 60), tokens=tokens, **kw))
    t.add_ws_handler(admin.WS_PATH, admin.make_ws_handler(tokens=tokens, on_change=changed.append, **kw))
    t.start()
    yield t, tokens, changed, shops_root, auth_file
    t.close()


def get(t, path, password=PASSWORD, user="admin"):
    req = urllib.request.Request(f"http://127.0.0.1:{t.port}{path}")
    if password is not None:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def token(t):
    status, body = get(t, "/admin/token")
    assert status == 200
    return json.loads(body)["token"]


def open_socket(t, tok, origin=None):
    headers = {"Origin": origin} if origin else {}
    ws = connect(f"ws://127.0.0.1:{t.port}/admin/ws", additional_headers=headers, open_timeout=5)
    ws.send(json.dumps({"cmd": "hello", "token": tok}))
    return ws


def ask(ws, **msg):
    msg.setdefault("id", 1)
    ws.send(json.dumps(msg))
    return json.loads(ws.recv(timeout=5))


@pytest.fixture
def ws(env):
    t = env[0]
    sock = open_socket(t, token(t), origin=f"http://127.0.0.1:{t.port}")
    assert json.loads(sock.recv(timeout=5)) == {"type": "ready"}
    yield sock
    sock.close()


def closed_after_hello(t, tok, origin=None):
    """The server may close before or after the hello is sent; either way the connection must end without a 'ready'."""
    with pytest.raises(ConnectionClosed):
        sock = open_socket(t, tok, origin)
        sock.recv(timeout=5)


# ---- the token ---------------------------------------------------------------

def test_the_token_needs_the_admin_password(env):
    t = env[0]
    assert get(t, "/admin/token", password=None)[0] == 401
    assert get(t, "/admin/token", password="wrong")[0] == 401
    assert get(t, "/admin/token", password=PASSWORD, user="alpha")[0] == 401


def test_each_token_is_different_and_long(env):
    t = env[0]
    a, b = token(t), token(t)
    assert a != b and len(a) >= 32


def test_an_expired_token_is_refused_and_the_store_cannot_grow_without_bound():
    now = [0.0]
    store = admin.TokenStore(ttl=10, clock=lambda: now[0])
    tok = store.issue()
    assert store.valid(tok)
    now[0] = 11
    assert not store.valid(tok)
    for _ in range(admin.MAX_TOKENS * 3):
        store.issue()
    assert len(store._tokens) <= admin.MAX_TOKENS
    assert not store.valid(None) and not store.valid(123) and not store.valid("made-up")


# ---- who may open the socket -------------------------------------------------

@pytest.mark.parametrize("tok", ["", "made-up", None, 5])
def test_a_wrong_token_closes_the_socket(env, tok):
    closed_after_hello(env[0], tok)


def test_a_connection_that_says_nothing_useful_is_closed(env):
    sock = connect(f"ws://127.0.0.1:{env[0].port}/admin/ws", open_timeout=5)
    sock.send(json.dumps({"cmd": "create_shop", "name": "sneaky"}))          # a command before signing in
    with pytest.raises(ConnectionClosed):
        sock.recv(timeout=5)
    assert not shops.exists("sneaky", env[3])


def test_a_page_on_another_site_cannot_use_the_socket_even_with_a_real_token(env):
    t = env[0]
    closed_after_hello(t, token(t), origin="http://evil.example")
    closed_after_hello(t, token(t), origin=f"http://127.0.0.1.evil.example:{t.port}")


def test_a_page_of_this_server_can(env):
    t = env[0]
    sock = open_socket(t, token(t), origin=f"http://127.0.0.1:{t.port}")
    assert json.loads(sock.recv(timeout=5)) == {"type": "ready"}
    sock.close()


def test_with_no_admin_password_the_socket_is_closed_even_with_a_token(env, monkeypatch):
    t = env[0]
    tok = token(t)
    monkeypatch.delenv("ADMIN_PASSWORD")
    closed_after_hello(t, tok)


def test_origin_check_function():
    assert admin.origin_ok({"Host": "a:1"})                                   # no Origin: not a browser
    assert admin.origin_ok({"Origin": "http://a:1", "Host": "a:1"})
    assert not admin.origin_ok({"Origin": "http://b:1", "Host": "a:1"})
    assert not admin.origin_ok({"Origin": "http://a:1"})                      # an Origin with no Host is not trusted
    assert not admin.origin_ok({"Origin": "null", "Host": "a:1"})


# ---- commands, end to end ----------------------------------------------------

def test_creating_a_shop_makes_it_and_tells_the_agent(env, ws):
    _, _, changed, shops_root, auth_file = env
    reply = ask(ws, cmd="create_shop", name="new_shop", display_name="New Shop", template="alpha", pin="4321")
    assert reply["ok"] and reply["pin"] == "4321" and reply["id"] == 1
    assert shops.exists("new_shop", shops_root) and auth.check_pin("new_shop", "4321", auth_file)
    assert changed == ["new_shop"]


def test_a_generated_pin_comes_back_in_the_reply(env, ws):
    reply = ask(ws, cmd="create_shop", name="shop_two", display_name="Shop Two")
    assert reply["ok"] and reply["pin_generated"] and len(reply["pin"]) == 6


def test_a_refused_command_says_why_and_changes_nothing(env, ws):
    _, _, changed, shops_root, _ = env
    reply = ask(ws, cmd="create_shop", name="alpha", display_name="Again")
    assert reply["ok"] is False and "already exists" in reply["error"]
    assert changed == []


def test_set_pin_save_prompt_and_save_stock_work_and_each_tells_the_agent(env, ws):
    _, _, changed, shops_root, auth_file = env
    assert ask(ws, cmd="set_pin", shop="alpha", pin="5555")["ok"] and auth.check_pin("alpha", "5555", auth_file)
    assert ask(ws, cmd="save_prompt", shop="alpha", system_prompt="Be brief.", display_name="Alpha Two")["ok"]
    assert ask(ws, cmd="save_stock", shop="alpha", update=[{"sku": "RICE-1KG", "price": 70}])["ok"]
    got = ask(ws, cmd="get_shop", shop="alpha")
    assert got["ok"] and got["system_prompt"].strip() == "Be brief." and got["stock"][0]["price"] == 70
    assert changed == ["alpha", "alpha", "alpha"]                            # get_shop changes nothing


def test_marking_a_warning_solved_and_bringing_it_back(env, ws):
    t = env[0]
    reply = ask(ws, cmd="dismiss", id_="x")                                  # not the right field: refused, not a crash
    assert reply["ok"] is False
    assert ask(ws, cmd="dismiss", id="alpha:no-pin", note="later")["ok"]
    data = json.loads(get(t, "/admin/data")[1])
    assert [p["id"] for p in data["solved"]] == ["alpha:no-pin"] and data["solved"][0]["note"] == "later"
    assert "alpha:no-pin" not in [p["id"] for p in data["problems"]]
    assert ask(ws, cmd="restore", id="alpha:no-pin")["ok"]
    data = json.loads(get(t, "/admin/data")[1])
    assert data["solved"] == [] and "alpha:no-pin" in [p["id"] for p in data["problems"]]


def test_marking_solved_stops_a_shop_needing_attention(env, ws):
    t = env[0]
    state = lambda: {s["name"]: s["state"] for s in json.loads(get(t, "/admin/data")[1])["shops"]}["alpha"]
    assert state() == "attention"                                            # no PIN
    ask(ws, cmd="dismiss", id="alpha:no-pin")
    assert state() == "ready"


def test_an_unknown_command_and_odd_messages_do_not_crash_the_socket(env, ws):
    assert ask(ws, cmd="delete_everything")["ok"] is False
    assert ask(ws, cmd=None)["ok"] is False
    ws.send("not json")
    ws.send(json.dumps([1, 2, 3]))
    assert ask(ws, cmd="get_shop", shop="alpha", id=9)["id"] == 9             # still alive and in step


def test_commands_are_rate_limited(env, ws, monkeypatch):
    monkeypatch.setattr(admin, "COMMANDS_PER_MINUTE", 3)
    replies = [ask(ws, cmd="get_shop", shop="alpha", id=i) for i in range(5)]
    assert [r["ok"] for r in replies] == [True, True, True, False, False]
    assert "Too many" in replies[-1]["error"]


def test_a_failing_agent_hook_does_not_fail_the_command(env, ws):
    """If telling the agent fails, the change on disk is still done and still reported as done."""
    env[2].fail = True
    reply = ask(ws, cmd="save_prompt", shop="alpha", system_prompt="Fine.", display_name="Alpha")
    assert reply["ok"] is True
    assert "Fine." in (env[3] / "alpha" / "config.yaml").read_text(encoding="utf-8")


def test_every_change_made_through_the_socket_is_in_the_activity_list_and_no_secret_is(env, ws):
    t = env[0]
    ask(ws, cmd="create_shop", name="new_shop", display_name="New Shop", pin="424242")
    ask(ws, cmd="set_pin", shop="alpha", pin="737373")
    ask(ws, cmd="save_prompt", shop="alpha", system_prompt="TOP SECRET WORDS", display_name="Alpha")
    ask(ws, cmd="get_shop", shop="alpha")                                    # reading is not an event
    ask(ws, cmd="create_shop", name="alpha", display_name="Dup")             # a refused command is not an event
    body = get(t, "/admin/data")[1]
    activity = json.loads(body)["activity"]
    assert [e["kind"] for e in activity] == ["save_prompt", "set_pin", "create_shop"]
    assert [e["shop"] for e in activity] == ["alpha", "alpha", "new_shop"]
    for secret in ("424242", "737373", "TOP SECRET"):
        assert secret not in body
