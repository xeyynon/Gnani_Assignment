# Plan of action: Nov 2 to Nov 9

**Goal:** a working Dukaan Dost that takes a shop order by voice in Hinglish, Hindi, Telugu and English on Gnani's Prisma and Timbre; an evaluation with real numbers; a 60-second demo video; the posts out by about Nov 5; the submission in on Nov 9 (hard deadline Nov 10, 11:59 PM IST).

**Written 2026-11-02.** Update the status column as work lands. Rule R-5 applies to everything below: nothing is claimed that a saved run does not show.

## Who owns what
| Area | Owner | Files |
|---|---|---|
| **UI and UX** (call page, shopkeeper dashboard, admin dashboard if built, look and feel, `MD/frontend.md`) | **The other session** | `dukaan_dost/web/`, `tests/web/`, `MD/frontend.md`, the page code in `transport_websocket.py` that serves them |
| **Everything behind the pages**: speech, model, order flow, evaluation, docs, CI | This session | the rest |

**The contract between the two** (neither side changes it without telling the other):
- Events the agent sends to the call page (`Transport.send_event`): `{"type": "user", "text", "lang"}`, `{"type": "agent", "reply", "text"}`, and `{"type": "order", "total", "items": [{"name", "qty", "unit", "line_total"}]}`.
- Files the agent writes for the dashboard: `orders/<shop>/order_<id>.json` in the format documented in `dukaan_dost/store.py`.
- Call link `/s/<shop>/`, dashboard `/s/<shop>/dashboard`, data at `/s/<shop>/dashboard/data`.

## The critical path
```
(1) the whole loop runs without a browser  ->  (2) evaluation numbers  ->  (3) README table  ->  (4) demo video + posts
        ReplayTransport                          20 scripts, clean+noisy       from saved runs         needs a real call
(1b) one real call in a browser with a microphone  ---------------------------------------------^   (with the UI session)
```
Step 1 matters most: it turns "the pieces work" into "the loop works", and it is what the evaluation runs on.

## Workstreams
Status: ⬜ not started · 🟡 in progress · ✅ done

### A. Run the whole loop without a browser (this session, Nov 2 to 3)
| # | Task | Status |
|---|---|---|
| A1 | `ReplayTransport` (DEC-048), 14 tests | ✅ 2026-11-02 |
| A2 | `evaluation/run_calls.py` (starts the real agent, plays the calls, saves the raw result) | ✅ 2026-11-03 |
| A3 | Measure time to first audio end to end, and find what the loop breaks on | 🟡 found B-26 (language list), B-27 (no order after call 1), B-30, B-31 |
| A4 | Fix what A3 finds | 🟡 B-26, B-27, B-28 fixed; B-30, B-31 open |

### B. Evaluation (this session, Nov 3 to 5)
| # | Task | Status |
|---|---|---|
| B1 | 20 order scripts, 65 turns, in `evaluation/scripts/orders.json` with the expected final order of each | ✅ 2026-11-03 |
| B2 | Audio from Timbre (generated and cached by `run_calls.py`); noise generated at a chosen SNR | ✅ 2026-11-03 |
| B3 | `evaluation/score_calls.py`, 10 tests (T-WER and cut-off rate not done) | ✅ 2026-11-03 |
| B4 | Run clean and noisy, save to `evaluation/results/` | 🟡 baseline clean run saved (45% exact, before the catalogue fix); the run with the fixes waits on Groq's daily limit (B-33); noisy run not started |
| B5 | Compare the language models if a Gemini key exists | ⬜ (waits on the key) |

### C. Features that score (this session, only after A and B are working)
| # | Task | Status | Cut rule |
|---|---|---|---|
| C1 | Loan guidance on the call: catch the project cost, read it back, speak the computed EMI (the calculator exists) | ⬜ | Cut if A or B slips past Nov 5 |
| C2 | Udhaar credit book: synthetic customers, limit check, balance in the order and the ledger | ⬜ | Cut first |
| C3 | A smaller prompt so more turns fit in Groq's limit | 🟡 order prompt cut 42 percent (DEC-041), then the catalogue added back about 1,100 tokens (DEC-042); search mode cuts the product part by about 90 percent ([rag_plan.md](rag_plan.md)) | Do if B4 is rate-limited |

### D. Real-world checks (needs Surya, with the UI session)
| # | Task | Status |
|---|---|---|
| D1 | One real call in a browser with a microphone; note gaps between clips, echo, interruptions (B-08, B-09) | ⬜ |
| D2 | A native speaker checks the Hindi and Telugu in `stock.json` and the sentences in `order_session.py` (B-16) | ⬜ |
| D3 | Read GitHub CI results and report red jobs (B-10) | ⬜ |
| D4 | A Gemini key, to compare against Groq | ⬜ |

### E. Submission material (Nov 5 to 9)
| # | Task | Owner | Status |
|---|---|---|---|
| E1 | README: problem, architecture diagram, how Prisma and Timbre are used, results table from saved runs, how to run, synthetic-data note | this session | ⬜ |
| E2 | 60-second demo video: a real call, Hinglish order, one interruption, the total read back, the dashboard | Surya (with the UI session's pages) | ⬜ |
| E3 | 2 to 3 minute walkthrough: architecture and the results table | Surya | ⬜ |
| E4 | LinkedIn and X posts, tagged Gnani AI with #GreatIndianAIInternshipChallenge #GnaniAI, **live before submitting** | Surya | ⬜ |
| E5 | Submission form: title, problem, target users, the Gnani models used, post links | Surya | ⬜ |

## Day by day
| Day | Goal | Done when |
|---|---|---|
| **Nov 2 (today)** | Plan; A1, A2 started | ReplayTransport exists and a scripted call runs through the real agent |
| **Nov 3** | A3, A4, B1, B2 | A full scripted order is spoken, understood and saved, with a measured time to first audio |
| **Nov 4** | B3, B4 | The first full clean run is saved; D1 attempted with the UI session |
| **Nov 5** | Noisy run; posts | Results exist; the demo video is recorded; **posts go out** |
| **Nov 6** | C1 if on track; fix what the results show | |
| **Nov 7** | README results table; videos finished | README has only numbers from saved runs |
| **Nov 8** | Buffer; final checks; CI green | `pytest`, `node --test`, `check_repo`, `check_docs` all pass |
| **Nov 9** | **Submit** | Form sent |

## Definition of done for the submission
1. A call in the browser takes an order in at least Hinglish and Telugu, reads the total back, and the order appears on the dashboard.
2. `evaluation/results/` holds the saved runs; every figure in the README, the videos and the posts comes from them.
3. The README is complete; all data is synthetic; no keys, no real numbers, no earlier-project material in the repo.
4. The posts are live and the videos exist.

## Risks and what we do about them
| Risk | Effect | Response |
|---|---|---|
| Groq limits (8,000 tokens a minute) | Evaluation takes hours; a demo with fast turns could be refused | Pace the runner; shrink the prompt (C3); use Gemini when a key exists |
| The model preview or availability changes | Groq may withdraw a model | Default is a production model (`gpt-oss-20b`); Gemini is the fallback |
| The loop breaks on a real call (echo, cut-offs, gaps) | The demo fails | A3 and D1 early; keep the browser's echo cancellation; tune VAD from measurements |
| Accuracy is lower than hoped | Weak results table | Report it honestly (R-5); improve the instructions and the number-word handling; the awards still count the attempt and the evaluation method |
| Time runs out | Features unfinished | Cut order: C2, then C1, then the optional items; A, B, E are not cut |
| The UI session and this one change the same file | Lost work | The ownership table above; shared contracts only change by message |

## Optional (only with spare time)
Admin dashboard (the UI session decides), several simultaneous calls, a real phone number through a telephony provider, a warm TTS connection (B-14), code-chosen alternatives for out-of-stock items, Hindi and Telugu dashboard labels.
