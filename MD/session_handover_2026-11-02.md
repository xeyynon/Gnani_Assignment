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
