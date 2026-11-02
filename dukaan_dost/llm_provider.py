"""
llm_provider.py

Chooses the language model with the LLM_PROVIDER environment variable: "gemini" (default) or
"groq" (see llm_groq.py). Both expose ask(), ask_json(), stream() and warmup(); conversation_manager.py and
app.py import from here and never from a specific backend.
"""

import logging
import os

log = logging.getLogger("llm_provider")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()

if LLM_PROVIDER == "gemini":
    from . import llm_gemini as _backend
elif LLM_PROVIDER == "groq":
    from . import llm_groq as _backend
else:
    raise ValueError(f"LLM_PROVIDER={LLM_PROVIDER!r} is not a known backend (expected 'gemini' or 'groq')")

log.info(f"[LLM-PROVIDER] Using backend: {LLM_PROVIDER}")

ask = _backend.ask
ask_json = _backend.ask_json
stream = _backend.stream
warmup = _backend.warmup
api_key = _backend.api_key
