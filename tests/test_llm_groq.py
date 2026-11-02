"""
Tests for the Groq language-model backend and the LLM provider switch, run against a stand-in HTTP
server that streams the OpenAI-style server-sent events Groq documents.

    python -m pytest tests/test_llm_groq.py
"""

import importlib
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import llm_groq  # noqa: E402

MESSAGES = [{"role": "system", "content": "You are a shopkeeper."}, {"role": "user", "content": "do kilo atta"}]


def sse(*pieces, done=True):
    out = b""
    for p in pieces:
        out += b"data: " + json.dumps({"choices": [{"delta": {"content": p}}]}).encode() + b"\n\n"
    if done:
        out += b"data: [DONE]\n\n"
    return out


class FakeGroq:
    """A stand-in server. `script` is a list of (status, headers, body) answered in order."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                status, headers, payload = outer.script.pop(0) if outer.script else (500, {}, b"no script")
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}/openai/v1"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)


def point_at(server, monkeypatch):
    monkeypatch.setenv("GROQ_BASE_URL", server.url)


def completion(text):
    return json.dumps({"choices": [{"message": {"role": "assistant", "content": text}}]}).encode()


# ---- streaming -------------------------------------------------------------------------------

def test_stream_yields_the_pieces_in_order_and_stops_at_done(monkeypatch):
    with FakeGroq([(200, {"Content-Type": "text/event-stream"}, sse("Do ", "kilo ", "atta.") + b"data: ignored\n\n")]) as s:
        point_at(s, monkeypatch)
        assert list(llm_groq.stream("llama-3.3-70b-versatile", MESSAGES, 100, 0.5)) == ["Do ", "kilo ", "atta."]
    req = s.requests[0]
    assert req["path"].endswith("/chat/completions") and req["auth"] == "Bearer test-key"
    assert req["body"]["stream"] is True and req["body"]["max_tokens"] == 100 and req["body"]["temperature"] == 0.5
    assert req["body"]["model"] == "llama-3.3-70b-versatile"
    assert req["body"]["messages"] == MESSAGES


def test_empty_and_role_only_pieces_are_skipped(monkeypatch):
    body = (b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n' + sse("", "Hello") +
            b"data: not json\n\n" + b'data: {"choices":[]}\n\n' + b"data: [DONE]\n\n")
    with FakeGroq([(200, {}, body)]) as s:
        point_at(s, monkeypatch)
        assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == ["Hello"]


def test_messages_with_unknown_roles_are_dropped(monkeypatch):
    messages = MESSAGES + [{"role": "tool", "content": "x"}]
    with FakeGroq([(200, {}, sse("ok"))]) as s:
        point_at(s, monkeypatch)
        list(llm_groq.stream("m", messages, 10, 0.1))
    assert s.requests[0]["body"]["messages"] == MESSAGES


def test_a_failure_before_any_text_is_retried_once(monkeypatch):
    with FakeGroq([(500, {}, b"boom"), (200, {}, sse("Namaste."))]) as s:
        point_at(s, monkeypatch)
        assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == ["Namaste."]
    assert len(s.requests) == 2


def test_a_rate_limit_with_a_short_wait_is_retried(monkeypatch):
    with FakeGroq([(429, {"retry-after": "0"}, b"slow down"), (200, {}, sse("ok."))]) as s:
        point_at(s, monkeypatch)
        assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == ["ok."]


def test_a_rate_limit_with_a_long_wait_is_not_waited_for(monkeypatch):
    with FakeGroq([(429, {"retry-after": "30"}, b"x"), (429, {"retry-after": "30"}, b"x")]) as s:
        point_at(s, monkeypatch)
        t0 = time.monotonic()
        assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == []
        assert time.monotonic() - t0 < 5


def test_a_failure_after_text_is_not_retried_so_nothing_is_said_twice(monkeypatch):
    cut_short = sse("Do kilo", done=False)          # the stream ends with no [DONE]: treated as the end, no repeat
    with FakeGroq([(200, {}, cut_short), (200, {}, sse("SECOND ATTEMPT"))]) as s:
        point_at(s, monkeypatch)
        assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == ["Do kilo"]
    assert len(s.requests) == 1


def test_all_attempts_failing_gives_an_empty_stream_not_an_exception(monkeypatch):
    with FakeGroq([(500, {}, b"a"), (500, {}, b"b")]) as s:
        point_at(s, monkeypatch)
        assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == []


def test_an_unreachable_server_gives_an_empty_stream(monkeypatch):
    monkeypatch.setenv("GROQ_BASE_URL", "http://127.0.0.1:9/openai/v1")
    assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == []


# ---- blocking ------------------------------------------------------------------------------------

def test_ask_returns_the_trimmed_reply(monkeypatch):
    with FakeGroq([(200, {}, completion("  Ji, bilkul.  "))]) as s:
        point_at(s, monkeypatch)
        assert llm_groq.ask("m", MESSAGES, 10, 0.1) == "Ji, bilkul."
    assert s.requests[0]["body"]["stream"] is False


def test_ask_retries_once_and_then_gives_an_empty_string(monkeypatch):
    with FakeGroq([(500, {}, b"a"), (500, {}, b"b")]) as s:
        point_at(s, monkeypatch)
        assert llm_groq.ask("m", MESSAGES, 10, 0.1) == ""
    assert len(s.requests) == 2


# ---- request details ----------------------------------------------------------------------------------

def test_reasoning_models_get_a_low_reasoning_effort_and_others_do_not(monkeypatch):
    with FakeGroq([(200, {}, sse("a")), (200, {}, sse("b")), (200, {}, sse("c"))]) as s:
        point_at(s, monkeypatch)
        list(llm_groq.stream("openai/gpt-oss-20b", MESSAGES, 10, 0.1))
        monkeypatch.setenv("LLM_REASONING_EFFORT", "medium")
        list(llm_groq.stream("openai/gpt-oss-120b", MESSAGES, 10, 0.1))
        list(llm_groq.stream("llama-3.3-70b-versatile", MESSAGES, 10, 0.1))
    assert s.requests[0]["body"]["reasoning_effort"] == "low"
    assert s.requests[1]["body"]["reasoning_effort"] == "medium"
    assert "reasoning_effort" not in s.requests[2]["body"]


def test_a_missing_key_is_reported_clearly(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")
    assert llm_groq.api_key() == ""
    assert list(llm_groq.stream("m", MESSAGES, 10, 0.1)) == []          # logged, no crash
    llm_groq.warmup("m")                                                 # no crash either


def test_a_placeholder_key_counts_as_unset(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "your-groq-api-key-here")
    assert llm_groq.api_key() == ""


def test_warmup_makes_one_small_request(monkeypatch):
    with FakeGroq([(200, {}, completion("hi"))]) as s:
        point_at(s, monkeypatch)
        llm_groq.warmup("llama-3.3-70b-versatile")
    assert len(s.requests) == 1 and s.requests[0]["body"]["max_tokens"] == 1


def test_warmup_failure_is_not_fatal(monkeypatch):
    monkeypatch.setenv("GROQ_BASE_URL", "http://127.0.0.1:9/openai/v1")
    llm_groq.warmup("m")


# ---- the provider switch -------------------------------------------------------------------------------

def test_the_default_provider_is_gemini(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    from dukaan_dost import llm_provider
    importlib.reload(llm_provider)
    assert llm_provider.LLM_PROVIDER == "gemini"


def test_the_groq_provider_exposes_the_same_names(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    from dukaan_dost import llm_provider
    try:
        importlib.reload(llm_provider)
        assert llm_provider.stream is llm_groq.stream and llm_provider.ask is llm_groq.ask
        assert llm_provider.warmup is llm_groq.warmup and llm_provider.api_key is llm_groq.api_key
    finally:
        monkeypatch.delenv("LLM_PROVIDER")
        importlib.reload(llm_provider)


def test_an_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nonsense")
    from dukaan_dost import llm_provider
    try:
        with pytest.raises(ValueError, match="groq"):
            importlib.reload(llm_provider)
    finally:
        monkeypatch.delenv("LLM_PROVIDER")
        importlib.reload(llm_provider)


def test_both_backends_have_the_functions_the_conversation_manager_uses():
    from dukaan_dost import llm_gemini
    for name in ("ask", "stream", "warmup", "api_key"):
        assert callable(getattr(llm_groq, name)) and callable(getattr(llm_gemini, name))


# ---- startup check ---------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


def test_groq_without_a_key_is_reported_at_startup(app, monkeypatch):
    monkeypatch.setattr(app, "_LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY")
    assert "GROQ_API_KEY" in app._llm_problem()
    monkeypatch.setenv("GROQ_API_KEY", "abc")
    assert app._llm_problem() is None


def test_gemini_without_credentials_still_reports_and_mentions_groq(app, monkeypatch):
    monkeypatch.setattr(app, "_LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    message = app._llm_problem()
    assert "GEMINI_API_KEY" in message and "LLM_PROVIDER=groq" in message
