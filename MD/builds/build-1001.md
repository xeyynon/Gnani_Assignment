# Build 1001: Gnani and Gemini keys, Gemini by API key, call recording off by default

**Date:** 2026-10-28

## What changed
The agent can now run on a Gemini API key with no Google Cloud project, and the Gemini model is a setting that defaults to a current model on that path. The config and requirements are ready for Gnani, and calls are no longer recorded unless someone turns recording on.

## Why
Setup for the Gnani build (step 1): new Gemini keys may not get gemini-2.5-flash (B-06), a Google Cloud project is a needless hurdle (DEC-025), and the contest allows synthetic data only, so recording must be opt-in (DEC-007, B-03). Also fixes the startup check that missed the example placeholder (B-01).

## How it was verified
13 offline tests (tests/test_llm_client.py) cover the client choice and the thinking settings; the new startup logic was run in isolation against six config cases (no file, placeholders, real keys, env over config, model override, recording opt-in). Not run against a live Gemini or Gnani key, and not on the Pi: whether a 3.x model accepts the thinking_level setting is still to be confirmed.

## What to improve next
Run the smoke test with real keys (also confirms the Gemini model and thinking setting), then the Gnani STT and TTS backends.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/DukaanDost_MASTER.md
- `M` MD/bugs.md
- `M` MD/external_research.md
- `M` MD/tasks.md
- `M` MD/tried_and_implemented.md
- `M` ai_caller_final3.py
- `M` companies/core/llm_gemini.py
- `M` local_config.example.py
- `M` requirements.txt
- `A` tests/test_llm_client.py
