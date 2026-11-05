# Build 1013: The order code no longer lets a model repeat earlier changes, and a damaged credit ledger is never wiped

**Date:** 2026-11-05

## What changed
A bug hunt over the whole agent fixed about 30 defects that a caller or a shopkeeper could meet: the model copying earlier items into later turns (which doubled orders), a damaged udhaar ledger replaced by opening balances, a customer charged before the order was saved, ordinary shop talk starting loan mode, a new customer matched to a similar known name, partial removes leaving impossible quantities, a call that outlived its hang-up leaking into the next one, a dead Timbre connection stalling a sentence for half a minute, and the phone provider being sent the caller's words.

## Why
The first valid evaluation run (gpt-oss-20b) showed five of seven wrong orders were the model repeating earlier changes, and five finders working in parallel on the money, call, speech, phone and scoring code each reproduced defects before reporting them. Money and credit are decided by code, so the code has to hold even when the model misbehaves.

## How it was verified
1,138 Python tests and 102 page tests pass; the local CI copy passes lint, the Python 3.10 check and the package check. Every fix has a regression test that failed without it. A live call through the real Prisma, model and Timbre ran end to end with the fixes in; the Timbre spare-connection change was timed against the real service (first audio 141 to 250 ms after the first sentence). Not verified: the effect of the repeat guard on a full valid evaluation run (the first such run was cut short by the model's daily limit), and the 1.5 s speech-recogniser grace, which is a judgement.

## What to improve next
Take a valid clean run on each model after the fixes and read what is still wrong; find where steady background noise starts to break the end-of-speech detector (B-85); decide whether the one-word payment answers Prisma sometimes drops (B-83) need a second try.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/admin_actions.py
- `M` dukaan_dost/app.py
- `M` dukaan_dost/auth.py
- `M` dukaan_dost/conversation_manager.py
- `M` dukaan_dost/credit.py
- `M` dukaan_dost/envfile.py
- `M` dukaan_dost/knowledge_retriever.py
- `M` dukaan_dost/llm_groq.py
- `M` dukaan_dost/loan_session.py
- `M` dukaan_dost/loan_turn.py
- `M` dukaan_dost/order_session.py
- `M` dukaan_dost/order_turn.py
- `M` dukaan_dost/shops.py
- `M` dukaan_dost/stock.py
- `M` dukaan_dost/store.py
- `M` dukaan_dost/stt_gnani.py
- `M` dukaan_dost/transport_telephony.py
- `M` dukaan_dost/transport_websocket.py
- `M` dukaan_dost/tts_gnani.py
- `M` tests/test_admin_actions.py
- `M` tests/test_credit.py
- `M` tests/test_envfile.py
- `M` tests/test_knowledge_retriever.py
- `A` tests/test_lifecycle_fixes.py
- `M` tests/test_llm_groq.py
- `M` tests/test_loan_flow.py
- `M` tests/test_order_session.py
- `M` tests/test_order_turn.py
- `M` tests/test_shops_auth_store.py
- `M` tests/test_stt_gnani.py
- `M` tests/test_transport_telephony.py
- `M` tests/test_transport_websocket.py
- `M` tests/test_tts_gnani.py
