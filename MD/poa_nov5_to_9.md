# Plan of action: Nov 5 evening to Nov 9

**Written 2026-11-05, 21:00 IST.** It replaces the day-by-day table of [poa_final_week.md](poa_final_week.md) from here on (that file stays as the record of Nov 2 to 5). Rule R-5 applies to everything: no figure in the README, the videos or the posts that a saved run in `evaluation/results/` does not show.

**Clock.** The posts were due about today (Nov 5). Submission target Nov 9, hard deadline Nov 10, 11:59 PM IST. Four working days are left.

## Where things stand
| Area | State |
|---|---|
| Order flow, loan guidance, credit book, product search | Built, tested offline, committed (build-1011 and the commits after it) |
| Call page loan panel | Built by the UI session (`ce5900e`) |
| Phone transport | Built against a stand-in provider only (B-39); needs KYC, which has no promised time |
| Evaluation tooling | Replay caller, runner, scorer (with English-word WER and cut-off counts), retrieval benchmark |
| **Evaluation numbers** | **Only the old baseline exists**: 9 of 20 orders exactly right, taken before the catalogue and echo fixes. The three runs of Nov 4 were killed with the session and left nothing. |
| Real-microphone call | Never done (B-08, B-09) |
| Bug hunt | The Nov 4 workflow hit the 5-hour usage limit and found nothing. No new bugs were recorded from it. |
| Videos, posts, README results, form | Not started |

## The critical path
```
(1) evaluation runs  ->  (2) fix what they show  ->  (3) re-run the failing set  ->  (4) README table
       tonight               Nov 6                       Nov 7                        Nov 7
(5) one real call in a browser  ->  (6) 60 s demo video  ->  (7) posts live  ->  (8) walkthrough  ->  (9) form
          Nov 6 (Surya)               Nov 6 or 7               Nov 7                 Nov 8              Nov 9
```
Steps 1 to 4 are this session. Steps 5 to 9 need Surya; this session prepares the material for each so that each takes minutes, not hours.

## Workstreams
Status: ⬜ not started · 🟡 in progress · ✅ done

### 1. Evaluation (this session; runs while other work goes on)
Groq allows about 200,000 tokens a day per model, so each model gets about one full run a day. The runner works from a frozen copy of the tree, so fixes made while a run goes cannot change what it measures.
| # | Run | Model | Saved as | Status |
|---|---|---|---|---|
| 1.1 | Clean, 20 calls / 65 turns, all fixes | gpt-oss-20b (the default) | `INVALID_orders_clean_fixes_20b`, `INVALID_orders_clean_20b` | ❌ both INVALID: the model's daily limit ran out near the end (B-33); 16 of 20 exact on the second, read for causes only |
| 1.2 | Credit and loan calls (8 calls) | gpt-oss-120b | `credit_loans_clean_120b` | ✅ valid, 2026-11-06: 8 of 8 exactly right (earlier run `INCOMPLETE_credit_loans_120b` kept as evidence) |
| 1.3 | Noisy, 10 dB SNR, 20 calls | gpt-oss-120b | `INCOMPLETE_orders_noisy10db_120b` | ❌ INCOMPLETE and no turn was understood: the end-of-speech detector treats steady noise as speech (B-85). Next: 20 dB and 15 dB |
| 1.4 | Search mode (`ORDER_CATALOGUE=search`), 20 calls | gpt-oss-120b | `INVALID_orders_clean_search_120b` | ❌ INVALID, 2026-11-06: 3 requests refused in the last call (daily limit); 16 of 20 exact for causes only. Not repeated before the 120b budget returns |
| 1.5 | Re-run of the calls that fail, after the fixes | 20b, Nov 6 or 7 | `orders_clean_after_fixes_20b` | ⬜ |
| 1.6 | Prisma alone, 65 turns, four ways (clean or simulated phone line, language chosen or named) | no model | `stt_accuracy_prisma` | ✅ valid 2026-11-07; it led to naming the call's language (B-94) |
| 1.7 | **Valid full-call run, 20 calls, search mode** | gpt-oss-20b, from about 20:40 on Nov 8, nothing else on that model | `orders_clean_search_20b` | ⬜ the one number still missing for the README |

A run with any rate-limited request is flagged INVALID by the scorer and is not quoted (B-33).

### 2. Fix what the runs show (this session)
| # | Task | Status |
|---|---|---|
| 2.1 | Read the agent logs and result files; list every wrong call with its cause (hearing, model, code, script) | ✅ for the run of Nov 5: 5 of 7 wrong orders were the model repeating earlier changes (B-82), 1 a hearing error (B-24), 1 a dropped word (B-83) |
| 2.2 | Fix causes in code or prompt; each fix gets a regression test and a line in `bugs.md` | ✅ B-82 and the 40 other fixes of the bug hunt (Build 1013, InBul21) |
| 2.3 | Time to first audio (B-31): the model's wait and the 0.65 s hangover, tuned against the cut-off counts, one change at a time, only with a run behind each | ⬜ |
| 2.4 | B-30 (guarded, unproven) and B-34 are closed or re-scoped from the new numbers | ⬜ |

### 3. Bug-finding and fixing cycle (this session, in parallel with 1)
The Nov 4 attempt used 20 agents at once and hit the usage limit. This one is smaller and chosen by risk.
| # | Task | Status |
|---|---|---|
| 3.1 | Finders on the highest-risk code only: order and credit money paths, call lifecycle in `app.py`, the spare Timbre connection, the phone transport, the scorer (it makes every README number) | ✅ five finders, 2026-11-05 |
| 3.2 | Each finding is reproduced offline before it counts; a second pass tries to refute it | ✅ every finding was reproduced by its finder; I checked the money ones against the code before fixing |
| 3.3 | Confirmed bugs are fixed with a test; `bugs.md` (the register) and `bugfixed.md` (a dated log of each fix, its test and its commit) are updated in the same change | ✅ |
| 3.4 | Full suite, lint and page tests green after every batch (`python scripts/ci_local.py`) | ✅ 1,138 Python and 102 page tests; the local CI copy found one real failure (B-80) and passes after it |

### 4. Real-world checks (Surya, with the UI session)
| # | Task | Why it cannot be skipped | Status |
|---|---|---|---|
| 4.1 | One real call in Chrome with a microphone: allow the mic, say a Hinglish order, interrupt once, hear the total, hang up, see the order on the dashboard (B-08, B-09) | The demo video is this call. Gaps, echo and cut-offs are unknown until someone does it. | 🟡 two real PHONE calls made on Nov 7 (one saved an order); the browser call with a microphone is still ⬜ |
| 4.2 | A native Hindi and Telugu reader checks the sentences in `order_session.py`, the loan and credit sentences and the names in `stock.json` and `customers.json` (B-16) | Wrong wording on camera costs more than any missing feature | ⬜ |
| 4.3 | Open the GitHub Actions page and tell this session which jobs are red (B-10); set the `BANNED_TERMS` variable | The CI has run only on this machine | ⬜ |
| 4.4 | Decide on the phone line: it works on an Exotel trial number through a temporary tunnel (B-39 partly answered). If it is not shown working again by Nov 8 evening, the demo is the browser call. | The tunnel address changes whenever it restarts. | 🟡 |
| 4.5 | Check the loan scheme figures against the SIH problem statement (DEC-047) | The README states them only as indicative until then | ⬜ |

### 5. Submission material (this session writes, Surya publishes)
| # | Task | Status |
|---|---|---|
| 5.1 | README: problem, architecture diagram, how Prisma and Timbre are used, results table (from saved runs only), how to run, the synthetic-data note, honest limits | 🟡 results filled from valid runs on Nov 8 (Prisma alone, 8 credit and loan calls); the 20-call row waits for 1.7 |
| 5.2 | Post drafts for LinkedIn and X (tags: Gnani AI, #GreatIndianAIInternshipChallenge, #GnaniAI), with the list of claims each may use | ✅ in `submission_drafts.md`; the result blanks wait for a valid run |
| 5.3 | A shot list and spoken script for the 60-second demo, and an outline for the 2 to 3 minute walkthrough | ✅ in `submission_drafts.md` |
| 5.4 | Submission form answers drafted in one file: title, problem, target users, Gnani models used, links | ✅ in `submission_drafts.md` (Nov 8); the links are filled on the day |
| 5.5 | Surya records both videos, publishes the posts, sends the form | ⬜ Nov 6 to 9 |

### 6. Housekeeping (this session)
| # | Task | Status |
|---|---|---|
| 6.1 | Sweep `tasks.md`: tick what was built since it was last updated (the scripted caller, the warm Timbre connection, the shorter order prompt, the loan panel) | ✅ 2026-11-05 |
| 6.2 | A build for what callers notice (agent changes after build-1011) and an InBul for tools and docs, once the bug batch is in | ✅ Build 1013 and InBul21 |
| 6.3 | `MD/DukaanDost_MASTER.md`, the hand-over file and the status artifact updated on Nov 8 | ⬜ |
| 6.4 | `LICENSE` chosen (Surya) and the first push with tags (Surya says when) | ⬜ |

## Day by day
| Day | Goal | Done when |
|---|---|---|
| **Nov 5 (tonight)** | Runs 1.1 to 1.3 going; this plan; post drafts; demo script; bug cycle started | A result file exists for run 1.1; the drafts are in `MD/` |
| **Nov 6** | Read the results; fix the top causes; runs 1.4 and 1.5; **Surya: 4.1 real call, 4.4 phone decision** | A call works in a real browser; the demo can be recorded |
| **Nov 7** | README results table from the saved runs; fixes frozen by evening; **Surya: record the 60 s demo, publish the posts** | README has only measured numbers; posts live |
| **Nov 8** | Buffer: walkthrough video, final checks, CI green on GitHub, hand-over | `pytest`, page tests, repo and docs checks pass; every figure traced to a saved run |
| **Nov 9** | **Submit** | Form sent |
| Nov 10 | Spare day only. Nothing planned. | |

## Cut rules
If time runs out, cut from the top of this list and never from the bottom:
1. The phone line (B-39): the demo is the browser call.
2. The search-mode run (1.4) and the Gemini comparison.
3. Latency tuning beyond one measured change (2.3).
4. The 2 to 3 minute walkthrough shrinks to a 90-second screen recording with voice-over.
5. **Never cut:** a working live call for the video, the saved evaluation results, the README, the posts, the form.

## Risks
| Risk | Response |
|---|---|
| The runs show accuracy well under what the smoke tests suggested | Report it as measured (R-5); fix the top causes; the awards count the method and the honesty of the evaluation as well |
| Groq's daily token limit ruins a run again | The scorer marks it INVALID; wait for the next day; the order of runs puts the most important one (1.1) first |
| The usage limit on this session stops the bug-hunt agents again | A smaller finder set (3.1); results are written to the scratch folder as they land, so a stop loses little |
| The real browser call fails on echo, gaps or cut-offs | Found on Nov 6 with a full day to fix; fall back to headphones for the video |
| The UI session and this one edit the same file | The UI session owns `dukaan_dost/web/` and `tests/web/`; this session does not touch them; shared contracts change only by message |
| Posts go out late | Engagement is counted at the cut-off, so tonight and tomorrow matter more than polish; the drafts are ready tonight |
