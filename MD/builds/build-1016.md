# Build 1016: Phone callers are heard better, and an order survives a rate limit

**Date:** 2026-11-07

## What changed
The agent now names a Hindi or Telugu call's language to the speech recogniser, hears an empty turn again with the language named, switches to the other gpt-oss model when one is rate limited, keeps a record of every call, replaces the repeated 'Sorry, I did not catch that' with a question that moves the order on, uses a shorter greeting, and the demo shop sells atta loose by the kilo and in 5 and 10 kg bags.

## Why
The first two real phone calls (2026-11-07) showed short answers lost, the same apology three times in a row, a rate limit silencing a call, an empty dashboard after a call with no order, and 2 kg of atta priced as 10 kg.

## How it was verified
1,225 offline tests pass; a Prisma-alone run of 65 turns (evaluation/results/stt_accuracy_prisma) shows Telugu calls exactly right on 10 of 16 turns with the language named against 5 of 16 chosen automatically; two real phone calls through the Exotel trial number saved an order. Not yet confirmed on a real call after the language change.

## What to improve next
A third real call, a valid full-call evaluation once the Groq model budget allows, and the dashboard panel for the call records (UI session)

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/app.py
- `A` dukaan_dost/call_stats.py
- `M` dukaan_dost/conversation_manager.py
- `M` dukaan_dost/llm_groq.py
- `M` dukaan_dost/order_session.py
- `M` dukaan_dost/order_turn.py
- `M` dukaan_dost/store.py
- `M` shops/dukaan_dost/knowledge/products_pricing.md
- `M` shops/dukaan_dost/stock.json
- `A` tests/test_call_stats.py
- `M` tests/test_lifecycle_fixes.py
- `M` tests/test_llm_groq.py
- `M` tests/test_order_turn.py
