"""
llm_groq.py

Groq as the language model, with the same ask() / stream() / warmup() shape as
llm_gemini.py, so LLM_PROVIDER=groq (see llm_provider.py) is a drop-in switch.

Groq serves open models behind an OpenAI-style chat-completions API:
    POST https://api.groq.com/openai/v1/chat/completions
    Authorization: Bearer <GROQ_API_KEY>
    {"model", "messages": [{"role": system|user|assistant, "content"}], "max_tokens",
     "temperature", "stream": true}
and streams server-sent events: lines "data: {json}" whose choices[0].delta.content is the next
piece of text, ending with "data: [DONE]". The messages this project builds are already in that
shape, so they go through unchanged.

Model: qwen/qwen3.8-27b by default. console.groq.com/docs/models lists llama-3.3-70b-versatile as
a production model, but on Surya's account (checked with GET /models on 2026-11-02) it is not
available; the chat models that are: openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b.
The gpt-oss models reason first and spent a 60-token budget on reasoning alone (empty reply), which
is wrong for a phone call; Qwen answered directly and fast (about 300 to 900 ms to the first
sentence). Groq calls Qwen a preview model that may be withdrawn at short notice. Rate limits on this
account: 8,000 tokens a minute (about 1,300 tokens per turn with the shop prompt, so roughly five
turns a minute) and 1,000 requests a day. LLM_MODEL overrides the model. For openai/gpt-oss-* a low
reasoning effort is requested (LLM_REASONING_EFFORT).

Why Groq at all: Surya had no Gemini key on 2026-11-02 and asked to use Groq for now. Gemini
stays available (LLM_PROVIDER=gemini). Gnani has no public LLM, so the language model is
never a Gnani one in either case.
"""

import json
import logging
import os
import threading
import time

import httpx

log = logging.getLogger("llm_groq")

DEFAULT_MODEL = "qwen/qwen3.8-27b"
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
REQUEST_TIMEOUT_SEC = float(os.getenv("GROQ_TIMEOUT_SEC", "25"))
MAX_RETRY_WAIT_SEC = 2.0            # a 429 asking for a longer wait than this is not worth a phone call

_client = None
_client_lock = threading.Lock()


def api_key() -> str:
    """The Groq key, or "" when unset. A "your-..." placeholder counts as unset."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return "" if key.startswith("your-") else key


def _base_url() -> str:
    return os.environ.get("GROQ_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _get_client() -> httpx.Client:
    """One pooled connection set for the whole process, so calls after the first reuse the TLS connection."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client(timeout=httpx.Timeout(REQUEST_TIMEOUT_SEC, connect=5.0))
    return _client


def _payload(model: str, messages: list, max_tokens: int, temperature: float, stream: bool) -> dict:
    body = {
        "model": model,
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages
                     if m.get("role") in ("system", "user", "assistant")],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = os.environ.get("LLM_REASONING_EFFORT", "low")
    return body


def _headers() -> dict:
    key = api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set. Get a key at https://console.groq.com/keys.")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _retry_after(response: httpx.Response) -> float:
    try:
        return float(response.headers.get("retry-after", "1"))
    except ValueError:
        return 1.0


def warmup(model: str):
    """Opens the connection with a one-token request, so the first caller does not pay for it."""
    try:
        _headers()
    except RuntimeError as e:
        log.warning(f"[GROQ] {e}")
        return
    try:
        t0 = time.monotonic()
        r = _get_client().post(f"{_base_url()}/chat/completions", headers=_headers(),
                               json=_payload(model, [{"role": "user", "content": "hi"}], 1, 0.0, False))
        r.raise_for_status()
        log.info(f"[GROQ] Client warmed ({model}, {time.monotonic() - t0:.2f}s).")
    except Exception as e:
        log.warning(f"[GROQ] Warmup call failed (non-fatal, the first real call will just be cold): {e}")


def ask(model: str, messages: list, max_tokens: int, temperature: float) -> str:
    """Blocking call: the full reply text, or "" on failure. Retries once."""
    for attempt in (1, 2):
        try:
            r = _get_client().post(f"{_base_url()}/chat/completions", headers=_headers(),
                                   json=_payload(model, messages, max_tokens, temperature, False))
            if r.status_code == 429 and attempt == 1 and _retry_after(r) <= MAX_RETRY_WAIT_SEC:
                time.sleep(_retry_after(r))
                continue
            r.raise_for_status()
            return (r.json()["choices"][0]["message"].get("content") or "").strip()
        except Exception as e:
            log.error(f"[GROQ] attempt {attempt}/2 failed: {e}")
    return ""


def stream(model: str, messages: list, max_tokens: int, temperature: float):
    """
    Yields the reply as text pieces as Groq produces them. Retries once, but only if the
    failure comes before any text has been yielded: once a piece is out, the caller may
    already be speaking it, and starting over would repeat what the caller has heard.
    """
    for attempt in (1, 2):
        yielded_any = False
        try:
            with _get_client().stream("POST", f"{_base_url()}/chat/completions", headers=_headers(),
                                      json=_payload(model, messages, max_tokens, temperature, True)) as r:
                if r.status_code == 429 and attempt == 1 and _retry_after(r) <= MAX_RETRY_WAIT_SEC:
                    time.sleep(_retry_after(r))
                    continue
                if r.status_code >= 400:
                    r.read()
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                for line in r.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        piece = json.loads(data)["choices"][0]["delta"].get("content")
                    except (ValueError, KeyError, IndexError):
                        continue
                    if piece:
                        yielded_any = True
                        yield piece
                return
        except Exception as e:
            if yielded_any:
                log.error(f"[GROQ-STREAM] failed after partial output: {e}")
                return
            log.warning(f"[GROQ-STREAM] attempt {attempt}/2 failed before any output: {e}")
    log.error("[GROQ-STREAM] all attempts failed with no output")
