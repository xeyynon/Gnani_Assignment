# Build 1002: Run as software only: call from a browser, Raspberry Pi support removed

**Date:** 2026-10-28

## What changed
You now place a test call from a browser tab: python -m dukaan_dost serves a call page, and the microphone and the agent's replies travel over a WebSocket. The Raspberry Pi and Bluetooth setup, and the Pi install scripts, are gone.

## Why
Surya asked for a fully software-based project with no Raspberry Pi dependency (DEC-032). It also makes the project easy to run and try on any laptop, and removes the main reason for the long microphone mute.

## How it was verified
87 offline tests, including a real server with a stand-in browser client and the real recorder thread over a real socket. The page's resampler was checked at four sample rates. The real main() booted with the cloud warm-ups stubbed, served the page, accepted a call, and the watchdog detected it. NOT done: the page has not been opened in a real browser, and no real Gnani, Gemini, Sarvam or Google credentials were used, so no end-to-end call has been made.

## What to improve next
Try the page in Chrome and Firefox, then the Gnani speech backends, then re-tune the Bluetooth-era settings with measurements.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` .gitattributes
- `M` CLAUDE.md
- `M` MD/DukaanDost_MASTER.md
- `M` MD/agents.md
- `M` MD/architecture.md
- `M` MD/bugs.md
- `M` MD/decisions.md
- `M` MD/deployment.md
- `M` MD/external_research.md
- `M` MD/flow.md
- `M` MD/frontend.md
- `M` MD/intent.md
- `M` MD/ml.md
- `M` MD/origin.md
- `M` MD/pain.md
- `D` MD/pi_free_plan.md
- `M` MD/pipeline_reference.md
- `M` MD/poa-non-ml.md
- `M` MD/prd.md
- `M` MD/problem_statement-gap-plan.md
- `M` MD/problem_statement.md
- `M` MD/project_docs_guide.md
- `M` MD/session_handover_2026-10-28.md
- `M` MD/system_design_and_boundary.md
- `M` MD/tasks.md
- `A` MD/transport_plan.md
- `M` MD/tried_and_implemented.md
- `M` README.md
- `M` SETUP.md
- `D` deploy/INSTALL.md
- `D` deploy/RUNNING.md
- `D` deploy/dukaan-dost.service
- `D` deploy/setup_pi.sh
- `M` dukaan_dost/app.py
- `M` dukaan_dost/knowledge_retriever.py
- `M` dukaan_dost/stt_sarvam.py
- `M` dukaan_dost/transport.py
- `D` dukaan_dost/transport_pipewire.py
- `A` dukaan_dost/transport_websocket.py
- `A` dukaan_dost/web/index.html
- `M` evaluation/README.md
- `M` evaluation/profile_frame_cost.py
- `M` evaluation/stt_regression_test.py
- `M` requirements.txt
- `M` tests/test_transport.py
- `A` tests/test_transport_websocket.py
