# Build 1000: Baseline: Smart Caller voice agent, de-identified

**Date:** 2026-10-28

## What changed
The starting point for Dukaan Dost: the Smart Caller phone agent at its latest upstream version (2026-08-19), with every client name taken out. It answers calls in Telugu, Hindi and English with Sarvam STT, Gemini on Vertex AI and Google TTS.

## Why
Every later build is measured against a known, working agent. Building on it is DEC-001; making it Build 1000 is DEC-020.

## How it was verified
Compared file by file (ignoring line endings) with a fresh clone of upstream commit a69a3bf on 2026-10-26: the only differences are the removed client names. A search of the staged files for the client's name found nothing. Not run on the Pi from this repo yet.

## What to improve next
Gnani keys and dependencies, call recording off by default, then the Prisma and Timbre smoke test.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `A` .gitignore
- `A` README.md
- `A` RUNNING.md
- `A` ai_caller_final3.py
- `A` analyze_benchmark.py
- `A` benchmark_dataset.json
- `A` companies/core/__init__.py
- `A` companies/core/conversation_manager.py
- `A` companies/core/knowledge_retriever.py
- `A` companies/core/llm_gemini.py
- `A` companies/core/retry.py
- `A` companies/core/stt_google.py
- `A` companies/core/stt_provider.py
- `A` companies/core/stt_sarvam.py
- `A` companies/core/tts_google.py
- `A` companies/core/validator.py
- `A` deploy/INSTALL.md
- `A` deploy/ai-caller.service
- `A` deploy/setup_pi.sh
- `A` flow.md
- `A` local_config.example.py
- `A` requirements.txt
- `A` run_benchmark.py
- `A` stt_diagnose.py
- `A` stt_regression_test.py
- `A` tests/test_stop_e2e.py
- `A` tests/test_streaming_e2e.py
