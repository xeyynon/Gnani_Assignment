# Build 1005: Call page and dashboard redesign, with a live transcript

**Date:** 2026-11-02

## What changed
The call page is now a call screen with a timer, listening/thinking/speaking states, a waveform, a live transcript and an order panel. The shopkeeper dashboard has a side menu, icon tiles with change since yesterday, a 7-day sales chart and a needs-attention list. The server sends the caller's words and the agent's sentences to the page as they happen.

## Why
A bare card on the call page gave a viewer no way to see what the agent heard, and the dashboard was a plain list. Both are what the demo video and the judges will see.

## How it was verified
396 Python tests and 31 Node tests pass. Both pages rendered in headless Chrome at 1280, 1100, 700, 390 and 360 px, light and dark, with no horizontal overflow. Not tried with a real microphone (B-08) or on a real phone.

## What to improve next
Send order messages from the agent so Current order fills in; try a real call; Quick actions, Stock and Reports are shown as soon until the server can take writes.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `A` .env.example
- `M` MD/frontend.md
- `M` MD/tasks.md
- `M` SETUP.md
- `M` dukaan_dost/__init__.py
- `M` dukaan_dost/app.py
- `M` dukaan_dost/conversation_manager.py
- `M` dukaan_dost/demo_data.py
- `A` dukaan_dost/envfile.py
- `A` dukaan_dost/llm_groq.py
- `A` dukaan_dost/llm_provider.py
- `M` dukaan_dost/store.py
- `M` dukaan_dost/stt_gnani.py
- `M` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/web/index.html
- `A` evaluation/results/smoke_roundtrip_20261102_135552.json
- `A` evaluation/results/smoke_roundtrip_20261102_135739.json
- `A` evaluation/results/smoke_tts_20261102_135416.json
- `M` requirements.txt
- `M` scripts/gnani_smoke_test.py
- `M` shops/dukaan_dost/config.yaml
- `A` tests/conftest.py
- `A` tests/test_envfile.py
- `A` tests/test_llm_groq.py
- `M` tests/test_stt_gnani.py
- `M` tests/test_transport_websocket.py
- `M` tests/web/call_page.test.mjs
- `M` tests/web/dashboard.test.mjs
