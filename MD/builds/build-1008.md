# Build 1008: The order flow: the model reads the order and the code does the money

**Date:** 2026-11-02

## What changed
During an order the language model now answers with a structured note, and the code applies it, checks every item against the stock list, adds up the prices and speaks the amounts, so the total a caller hears is the total the dashboard shows. Finished orders are saved when the call ends and appear on the call page's order panel as they build up. Groq's gpt-oss model is the default language model, the shop prompt asks for digits, and the knowledge search ignores everyday words.

## Why
The model used to add up totals and speak them itself, which is where wrong amounts come from, and the dashboard showed only made-up data.

## How it was verified
558 Python tests pass, about 110 of them new for the order flow. Tried by hand against the real Groq models on Hinglish, Telugu and English orders: the amounts the code spoke were right, and gpt-oss returned valid structured answers every time. Those runs were informal and are not saved results, so no figure from them may be quoted. NOT done: the udhaar balance and limit check, choosing alternatives for out-of-stock items in code, and checking the Hindi and Telugu sentences the code speaks with a native speaker.

## What to improve next
Run the 20 evaluation scripts and save the results; build the udhaar check; have the spoken Hindi and Telugu sentences reviewed; watch the rate limit, which allows about four order turns a minute.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` .env.example
- `M` SETUP.md
- `M` dukaan_dost/app.py
- `M` dukaan_dost/conversation_manager.py
- `M` dukaan_dost/knowledge_retriever.py
- `M` dukaan_dost/llm_gemini.py
- `M` dukaan_dost/llm_groq.py
- `M` dukaan_dost/llm_provider.py
- `A` dukaan_dost/order_session.py
- `A` dukaan_dost/order_turn.py
- `M` dukaan_dost/stock.py
- `M` shops/dukaan_dost/config.yaml
- `M` tests/test_knowledge_retriever.py
- `M` tests/test_llm_groq.py
- `A` tests/test_order_app.py
- `A` tests/test_order_session.py
- `A` tests/test_order_turn.py
- `M` tests/test_shop_dukaan_dost.py
