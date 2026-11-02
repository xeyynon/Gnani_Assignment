# Build 1004: Gnani speech backends, the demo shop, and fixes found by the research

**Date:** 2026-11-02

## What changed
Prisma (listening) and Timbre (speaking) can now be switched in with STT_PROVIDER=gnani and TTS_PROVIDER=gnani. The agent has a demo kirana shop with a 61-item stock list in English, Hindi and Telugu. Three defects are fixed: a price was split from its currency word, an interrupted reply was remembered as fully heard, and Hindi and Telugu words were cut into pieces by the knowledge search. The dashboard shows when a customer is on a call.

## Why
The challenge needs a Gnani model in the pipeline, and the agent had no shop to run. Reading the code against the research found the three defects, which affect every call.

## How it was verified
355 Python tests and 20 page tests pass. The Gnani code runs against stand-in servers that follow the live docs; it has not been run against the real service (B-13). The interruption fix is tested as logic plus a check that the thread hooks exist; it has not been heard on a call.

## What to improve next
Run scripts/gnani_smoke_test.py with a key, then build the order flow so totals are computed in code (B-15).

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` SETUP.md
- `M` dukaan_dost/app.py
- `M` dukaan_dost/conversation_manager.py
- `M` dukaan_dost/dashboard.py
- `M` dukaan_dost/knowledge_retriever.py
- `M` dukaan_dost/preview.py
- `A` dukaan_dost/spoken_history.py
- `A` dukaan_dost/stock.py
- `A` dukaan_dost/stt_gnani.py
- `M` dukaan_dost/stt_provider.py
- `M` dukaan_dost/transport.py
- `M` dukaan_dost/transport_websocket.py
- `A` dukaan_dost/tts_gnani.py
- `A` dukaan_dost/tts_provider.py
- `M` dukaan_dost/web/dashboard.html
- `A` scripts/build_shop_knowledge.py
- `A` scripts/gnani_smoke_test.py
- `M` shops/README.md
- `A` shops/dukaan_dost/config.yaml
- `A` shops/dukaan_dost/knowledge/core/always_on.md
- `A` shops/dukaan_dost/knowledge/delivery_shipping.md
- `A` shops/dukaan_dost/knowledge/faq.md
- `A` shops/dukaan_dost/knowledge/ordering_payment.md
- `A` shops/dukaan_dost/knowledge/packaging.md
- `A` shops/dukaan_dost/knowledge/payment_issues.md
- `A` shops/dukaan_dost/knowledge/products_pricing.md
- `A` shops/dukaan_dost/knowledge/recommendations.md
- `A` shops/dukaan_dost/knowledge/refund_policy.md
- `A` shops/dukaan_dost/stock.json
- `A` tests/fake_ws.py
- `A` tests/test_knowledge_retriever.py
- `M` tests/test_preview.py
- `A` tests/test_sentence_split.py
- `A` tests/test_shop_dukaan_dost.py
- `A` tests/test_smoke_script.py
- `A` tests/test_spoken_history.py
- `M` tests/test_startup_checks.py
- `A` tests/test_stt_gnani.py
- `A` tests/test_tts_gnani.py
