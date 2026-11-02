"""
llm_gemini.py

Thin wrapper around Gemini that exposes both blocking and streaming
chat-completion style functions. Two ways to reach Gemini:
  - GEMINI_API_KEY set  -> the Gemini Developer API (no Google Cloud
                           project needed)
  - otherwise           -> Vertex AI (GOOGLE_CLOUD_PROJECT + ADC)

ask()    — blocking, returns full reply (used by repeat/translate paths)
stream() — yields text chunks as they arrive from Gemini (used by the
           main conversation path for streaming Gemini→TTS)
"""

import logging
import os
import threading

from google import genai
from google.genai import types

from .retry import with_retry

log = logging.getLogger("llm_gemini")

REQUEST_TIMEOUT_MS = 25_000

_client = None
# 2026-07-31: without this, warmup() racing an early real call from
# another thread could construct two genai.Client instances — the
# second silently discarding the first's already-warmed HTTP
# connection pool. Low likelihood (warmup normally finishes before
# calls start) but cheap to close outright rather than rely on timing.
_client_lock = threading.Lock()


def api_key() -> str:
    """
    The Gemini Developer API key, or "" when unset. A value still shaped
    like the placeholder in local_config.example.py ("your-...") counts
    as unset, so an unedited copy falls through to the Vertex path (and
    its clear startup error) instead of failing at the first request.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return "" if key.startswith("your-") else key


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                key = api_key()
                if key:
                    _client = genai.Client(api_key=key)
                else:
                    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-project-id-here")
                    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-south1")
                    _client = genai.Client(vertexai=True, project=project, location=location)
    return _client


def _thinking_config(model: str) -> types.ThinkingConfig:
    """
    Keep thinking as low as the model allows: this is a phone call, and
    every thinking token is latency before the first spoken word.

    gemini-2.5-* take a budget (0 switches thinking off). Google's docs
    (read 2026-10-28) describe only `thinking_level` for gemini-3.x, with
    "minimal" as the lowest level on 3.5 Flash-Lite and 3.6 Flash and
    "low" on 3.8 Flash, so a 3.x model gets a level instead of a budget.
    LLM_THINKING_LEVEL (minimal|low|medium|high) overrides it. Not yet
    tested against a live 3.x model: the smoke test covers it.
    """
    if model.startswith("gemini-2.5"):
        return types.ThinkingConfig(thinking_budget=0)
    default = "low" if model.startswith("gemini-3.8") else "minimal"
    level = os.environ.get("LLM_THINKING_LEVEL", default).strip().upper()
    if level not in ("MINIMAL", "LOW", "MEDIUM", "HIGH"):
        log.warning(f"[GEMINI] LLM_THINKING_LEVEL={level!r} is not valid; using {default}")
        level = default.upper()
    return types.ThinkingConfig(thinking_level=level)


def warmup(model: str):
    """
    Forces client construction (credential loading) AND a real, minimal
    generate_content call at process boot — unlike the STT/TTS clients,
    google-genai's HTTP connection pool is only actually opened on the
    first real request, so just constructing the client isn't enough to
    warm it. A 1-token throwaway call is a small, one-time cost per
    process start, in exchange for the first real caller not paying for
    connection setup on their own turn.
    """
    client = _get_client()
    try:
        client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part(text="hi")])],
            config=types.GenerateContentConfig(
                max_output_tokens=1,
                thinking_config=_thinking_config(model),
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
            ),
        )
        log.info("[GEMINI] Client warmed.")
    except Exception as e:
        log.warning(f"[GEMINI] Warmup call failed (non-fatal, first real call will just be cold): {e}")


def _split_system_and_turns(messages: list[dict]) -> tuple[str, list[types.Content]]:
    system_parts = []
    turns = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            turns.append(types.Content(role="user", parts=[types.Part(text=content)]))
        elif role == "assistant":
            turns.append(types.Content(role="model", parts=[types.Part(text=content)]))

    return "\n\n".join(system_parts), turns


def _make_config(model: str, max_tokens: int, temperature: float) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=None,  # set per-call
        max_output_tokens=max_tokens,
        temperature=temperature,
        thinking_config=_thinking_config(model),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )


def ask(model: str, messages: list[dict], max_tokens: int, temperature: float) -> str:
    """Blocking call — returns full reply text."""
    client = _get_client()
    system_instruction, turns = _split_system_and_turns(messages)

    config = _make_config(model, max_tokens, temperature)
    config.system_instruction = system_instruction

    try:
        response = with_retry(lambda: client.models.generate_content(
            model=model,
            contents=turns,
            config=config,
        ))
        return (response.text or "").strip()
    except Exception as e:
        log.error(f"[GEMINI] {e}")
        return ""


def ask_json(model: str, messages: list[dict], max_tokens: int, temperature: float, schema: dict | None = None) -> str:
    """Blocking call in JSON mode (the order turns): the JSON text, or "" on failure. `schema` is not used here yet:
    the JSON mime type alone is asked for."""
    client = _get_client()
    system_instruction, turns = _split_system_and_turns(messages)
    config = _make_config(model, max_tokens, temperature)
    config.system_instruction = system_instruction
    config.response_mime_type = "application/json"
    try:
        response = with_retry(lambda: client.models.generate_content(model=model, contents=turns, config=config))
        return (response.text or "").strip()
    except Exception as e:
        log.error(f"[GEMINI] {e}")
        return ""


def stream(model: str, messages: list[dict], max_tokens: int, temperature: float):
    """
    Streaming call — yields text chunks as Gemini generates them.
    Each chunk is a non-empty string fragment. Caller assembles the
    full reply by concatenating all yielded chunks.

    Retries once, but only if the failure happens before any chunk has
    been yielded. Once even one chunk has gone out, the caller (the
    processor thread) may already be synthesizing/queuing it for
    playback — restarting the call from scratch at that point would
    re-speak content the caller already heard, so a failure past that
    point is logged and simply ends the stream instead of retrying.
    """
    client = _get_client()
    system_instruction, turns = _split_system_and_turns(messages)

    config = _make_config(model, max_tokens, temperature)
    config.system_instruction = system_instruction

    attempts = 2
    for attempt in range(1, attempts + 1):
        yielded_any = False
        try:
            response_stream = client.models.generate_content_stream(
                model=model,
                contents=turns,
                config=config,
            )
            for chunk in response_stream:
                text = chunk.text
                if text:
                    yielded_any = True
                    yield text
            return
        except Exception as e:
            if yielded_any:
                log.error(f"[GEMINI-STREAM] failed after partial output: {e}")
                return
            log.warning(f"[GEMINI-STREAM] attempt {attempt}/{attempts} failed before any output: {e}")

    log.error("[GEMINI-STREAM] all attempts failed with no output")
