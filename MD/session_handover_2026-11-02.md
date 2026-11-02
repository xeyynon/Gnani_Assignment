# Session handover: 2026-11-02

Picks up from [session_handover_2026-10-28.md](session_handover_2026-10-28.md). **Nothing from the work below is committed.** The last commit is InBul13 (2026-10-28); `main` is two commits ahead of GitHub.

## Done since the last hand-over
| What | Where | Tests |
|---|---|---|
| **Live-calls strip** on the shopkeeper dashboard ("A customer is on a call (0:12)"). Each shop sees only its own calls, and only their length | `transport.live_calls()`, `dashboard.py`, `web/dashboard.html`, the preview shows a made-up call | 2 new |
| **Research**: papers behind each design choice, methods M1 to M11, corrections to earlier claims | [research_papers.md](research_papers.md) | n/a |
| **Pipeline expectations**: evidence per stage, targets, 7 first experiments | [pipeline_expectations.md](pipeline_expectations.md) | n/a |
| **Gnani speech backends** (DEC-035): Prisma STT, Timbre TTS, the provider switch, startup key check | `stt_gnani.py`, `tts_gnani.py`, `tts_provider.py`, `stt_provider.py`, `app.py` | 50 + 3 |
| **Smoke test** for the real services | `scripts/gnani_smoke_test.py` (`tts`, `roundtrip`, `stt`, `concurrency`) | 5 |
| **Three fixes the research found** (DEC-037): B-17 price split from its currency word, B-18 interrupted reply kept as heard, B-19 Hindi/Telugu words cut into pieces by retrieval | `conversation_manager.py`, `spoken_history.py`, `app.py`, `knowledge_retriever.py` | 12 + 14 + 14 |
| **The demo shop** (DEC-036): config, 61-item `stock.json`, generated `products_pricing.md`, all knowledge files; product names now go to Prisma when a call starts | `shops/dukaan_dost/`, `stock.py`, `scripts/build_shop_knowledge.py` | 31 |

Totals: 355 Python tests and 20 page tests pass. `check_repo.py` and `check_docs.py` pass.

## What the tests do not prove
- **The Gnani backends have never run against the real service** (B-13). The stand-in servers follow the live docs, so a pass means the code matches the docs, not that the service matches them.
- **The playback and processor threads can't be run in a unit test**, so the interruption fix (B-18) is covered by tests of the tracker plus a check that the hooks exist in `app.py`. It has not been heard on a call.
- **Nothing has been tried with a real Gemini key**, so the shop's prompt has never produced a real order reply.
- **Totals are added up by the model** (B-15); the rule layer that does it in code is the next big piece.
- **Hindi and Telugu product names are unchecked** (B-16).

## Blocked on Surya
1. **Gnani key** (app.gnani.ai/voice) and a **Gemini key** (aistudio.google.com/apikey). Everything real waits on these. Then run `python scripts/gnani_smoke_test.py roundtrip --save` and send the output.
2. Someone who reads Telugu and Hindi checks the names in `shops/dukaan_dost/stock.json`.
3. Decide when to commit. A suggested split, following the build / InBul rule:
   - **A build** for the user-visible changes: the Gnani backends, the shop, the three fixes, the live-calls strip.
   - **An InBul** for the research docs and tests, if you want them separate.
   Run `node scripts/changelog.mjs --pending` before the build commit.

## Next (in this order)
1. Gnani smoke test with the key; fix whatever it shows (B-13, B-14); fill in the measured numbers.
2. **Step 8: the order flow.** The model extracts item and quantity; code checks `stock.json`, adds the lines, speaks the total, writes `orders/<shop>/order_<id>.json` and `.txt` (this also fixes B-11 and B-15). Raise `LLM_HISTORY` (B-02).
3. Loan guidance on the call (the calculator exists, DEC-027).
4. Udhaar ledger (first thing cut if time runs short).
5. Evaluation: 20 scripts, clean and noisy, WER and T-WER, order accuracy, time to first audio (targets in [pipeline_expectations.md](pipeline_expectations.md)).
6. README results table, videos and the LinkedIn / X posts. **The posts were due about 2026-11-05**; the demo video needs a working call.
7. Admin dashboard (DEC-034) only if there is time; many simultaneous calls and a real phone number are stretch goals.

## Dates
Submission target 2026-11-09. Hard deadline 2026-11-10, 11:59 PM IST.

## Later the same day: real services, Groq, `.env`
Surya added the Gnani and Groq keys to `.env` (a loader in `dukaan_dost/envfile.py` reads it; the tests ignore it). Done:
- **Ran the smoke test against the real Prisma and Timbre** and fixed what it found: the service sends no `processing` message, so every utterance waited about 9 s; now about 0.4 s (B-22). Saved runs: `evaluation/results/`.
- **Groq as the language model** (`llm_groq.py`, `llm_provider.py`, DEC-038). The account's usable models are Qwen and gpt-oss; Qwen is the default. Tight limits (B-20).
- **Shop prompt changed to digits.** Timbre reads digits correctly; the model spells numbers wrongly. Checked on the real stack: totals were right on two orders.
- **Key terms narrowed** to the 61 main English names after the long list caused errors.
- Still true: **nothing from this section is committed** on top of Build 1004 / InBul14. Changed files include `stt_gnani.py`, `stock.py`, `config.yaml`, `app.py`, new `llm_groq.py`, `llm_provider.py`, `envfile.py`, tests and docs.

Next: the order flow (Step 8). It needs the Groq pacing in mind: the 20 evaluation scripts at about 5 turns a minute will take time (B-20).

## Evening: the order flow (DEC-039)
Built the order flow, the biggest piece left. **Nothing in this section is committed.**
- `order_session.py` (stock check, quantity rules, rounding, sentences in three languages, files), `order_turn.py` (instructions, strict JSON schema, reply assembly), JSON mode (`ask_json`) in both model backends, the conversation manager's order path, and the hooks in `app.py` (a fresh order per call, saved at hang-up). The call page's order panel is fed by `order` events.
- **What changed in behaviour:** the model no longer speaks free text during an order. It returns a JSON note; the code applies it and says the amounts. So a total a caller hears is always the dashboard's total (B-15 closed, B-11 closed for orders).
- **Tests:** 513 Python and 31 page tests pass (about 110 new, in `test_order_session.py`, `test_order_turn.py`, `test_order_app.py`, plus Groq JSON-mode tests).
- **Tried with the real model** (Groq Qwen, a six-turn Hinglish order, then Telugu and English): see "Real-model runs" below. These runs are informal and not saved results.
- **Known weaknesses:** the model sometimes answers in plain words and needs a retry (B-23); alternatives for out-of-stock items are still the model's (B-21); an order turn is about 2,000 tokens, so about four turns a minute on this Groq account (B-20); the Hindi and Telugu sentences the code speaks are unchecked (B-16).

### Real-model runs (informal, not saved results)
Six-turn Hinglish, four-turn Telugu and five-turn English orders on the real Groq model, paced to its rate limit.
- **Qwen preview:** the code's amounts were always right, but about one model call in four came back broken ('{done', '{"opts'); two Hinglish turns and one English turn ended in "didn't catch that" and lost an item or the payment. Also invented a ghee price and brands.
- **gpt-oss-20b (now the default) and 120b:** valid JSON every time, identical answers on the Hinglish order. Final orders correct: Hinglish 1 kg sugar (2 minus 1), 1 litre oil, 4 Maggi, total 265, Ramesh, cash, confirmed; Telugu rice, oil and 0.5 kg onion, 305, cash; English ghee, 330, UPI.
- **What the real runs changed:** the code now speaks the whole reply on any turn that touches the order (the model narrated changes twice, with totals of its own such as 209 beside the real 265, and invented a delivery time and an address); prices come from the stock list; the shop's own closing sentence is said when payment is chosen; unsold items are named; the placeholders became square brackets; the knowledge search ignores everyday words (it had missed ghee); the instructions list the Hindi and Telugu number words and say one op per item named.
- **First-sentence time:** about 0.6 to 1.3 s (one first turn took 3 s). Not a saved measurement.
- **Still weak:** a few conversations prove little (B-24). The model's own words are still used for questions about the shop, where it sometimes answers in English during a Hindi call.
