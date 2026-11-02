"""
tts_provider.py

Chooses the text-to-speech backend with the TTS_PROVIDER environment variable:
"google" (default, the backend the pipeline was built on) or "gnani" (Timbre,
see tts_gnani.py). Both expose the same four names, so app.py imports from
here and never from a specific backend:

    synthesize, warmup, start_streaming_synthesis, needs_digit_spelling
"""

import logging
import os

log = logging.getLogger("tts_provider")

TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "google").lower()

if TTS_PROVIDER == "google":
    from . import tts_google as _backend
elif TTS_PROVIDER == "gnani":
    from . import tts_gnani as _backend
else:
    raise ValueError(f"TTS_PROVIDER={TTS_PROVIDER!r} is not a known backend (expected 'google' or 'gnani')")

log.info(f"[TTS-PROVIDER] Using backend: {TTS_PROVIDER}")

synthesize = _backend.synthesize
warmup = _backend.warmup
start_streaming_synthesis = _backend.start_streaming_synthesis
needs_digit_spelling = _backend.needs_digit_spelling
