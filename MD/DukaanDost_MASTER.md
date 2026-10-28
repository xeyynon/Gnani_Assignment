# Dukaan Dost — MASTER

The one page to read first. Everything else in `MD/` hangs off this.

**Last updated:** 2026-10-28 · **Latest build:** 1000 · **Latest InBul:** InBul05

## What it is
Dukaan Dost is a phone-order voice agent for a neighbourhood kirana store. A customer rings the shop's phone, and the agent takes the order in Telugu, Hindi, English or code-mixed Hinglish. It checks each item against the shop's stock list, confirms quantities and prices, reads back the total in words, and writes an order summary for the shopkeeper. It also keeps the shop's **udhaar (credit) book** by phone: it records credit orders, tells regulars their balance and records promises to pay (DEC-026).

It is our entry for Gnani.ai's **Great Indian AI Internship Challenge**. Speech-to-text and text-to-speech run on Gnani's models (Prisma and Timbre). Reasoning stays on Gemini, because Gnani's own LLM (Evon) isn't on the public API.

## Key dates
| Date | What |
|---|---|
| 2026-10-26 | Project started from the Smart Caller codebase (this folder) |
| **2026-11-05** | LinkedIn and X posts out (shortlisting counts verified engagement) |
| **2026-11-09** | Our submission target |
| 2026-11-10, 11:59 PM IST | Hard deadline |

## Status at a glance
| Area | State |
|---|---|
| Base codebase | ✅ In place: the root folder is the latest upstream code (Aug 19, 2026) with client names removed. See [helpfromsmartcaller.md](helpfromsmartcaller.md) |
| Git and versioning | ✅ `main`, with Build 1000 (the baseline) and InBul01 (these docs and the changelog script). See [project_docs_guide.md](project_docs_guide.md) |
| Upstream clone out of the folder | ⚠️ The move failed (permission denied); excluded locally meanwhile (DEC-021) |
| CLAUDE.md in git | ⚠️ Untracked until the client name is taken out (DEC-022) |
| Gnani API key | ❌ Not registered yet |
| Smoke test (Prisma and Timbre) | ❌ Not started |
| `stt_gnani.py` / `tts_gnani.py` | ❌ Not started |
| Gemini via API key | ❌ Not started (Vertex only today) |
| Shop data (`companies/dukaan_dost/`) | ❌ Not started |
| Order summary output | ❌ Not started |
| Evaluation | ❌ Not started |
| README and SETUP | 🟡 Front page and setup written; results table waits for the eval |
| Videos, posts | ❌ Not started |

The live checklist is in [tasks.md](tasks.md).

**Research on 2026-10-28 changed the plan:** Prisma v3.0 (2026-10-22) detects the language itself and has a `commit` frame; Timbre now reads numbers itself; new Gemini keys may not get 2.5 Flash. Two risks to check first: B-06 and B-07. See [external_research.md](external_research.md).

## Document map
| File | Read it when |
|---|---|
| [project_docs_guide.md](project_docs_guide.md) | You need to know where things are written down, and how builds and InBuls work |
| [readme.md](readme.md) | You want the quick rules for writing in this folder |
| [../CHANGELOG.md](../CHANGELOG.md), [builds/](builds/) | You want what shipped in each build (generated; don't edit) |
| [../README.md](../README.md), [../SETUP.md](../SETUP.md) | The public front page; installing and running |
| [intent.md](intent.md) | You need the "why" in one page |
| [idea_research.md](idea_research.md) | You want to know why this idea, what the competing entries do, and the alternatives considered |
| [problem_research.md](problem_research.md) | You want the SIH 2026 and other problem statements mined for voice problems, the evidence for each, and the scored alternatives |
| [problem_statement.md](problem_statement.md) | You need the contest's rules, awards and judging |
| [problem_statement-gap-plan.md](problem_statement-gap-plan.md) | You want to know what's missing for each award we target |
| [prd.md](prd.md) | You need the product requirements: what the agent must do on a call |
| [architecture.md](architecture.md) | You need the components and how they connect |
| [flow.md](flow.md) | You need the step-by-step runtime flow (threads, per call, per utterance) |
| [frontend.md](frontend.md) | You're building the order viewer (planned) |
| [system_design_and_boundary.md](system_design_and_boundary.md) | You need to know what's in scope, what's out and where the trust boundaries are |
| [integration_handoff.md](integration_handoff.md) | You're writing a new STT, TTS or LLM backend and need the exact interface |
| [ml.md](ml.md) | You want the models in the stack and why each was chosen |
| [ml_model_integration.md](ml_model_integration.md) | You're wiring Prisma or Timbre in |
| [failmlmodel.md](failmlmodel.md) | Before trying a model: it may already have been ruled out |
| [poa-non-ml.md](poa-non-ml.md) | You want the plan for everything that isn't model work |
| [tasks.md](tasks.md) | You want the checklist |
| [decisions.md](decisions.md) | Before changing something that looks odd: it may be deliberate |
| [rules.md](rules.md) | Always. Hard rules for code, data and commits |
| [agents.md](agents.md) | You want the pipeline's agents (threads), or you're an AI coding agent working here |
| [bugs.md](bugs.md) | Known bugs and risks |
| [pain.md](pain.md) | The user's pain and ours |
| [deployment.md](deployment.md) | Setting up the Pi, keys and running |
| [external_research.md](external_research.md) | Facts from Gnani's, Sarvam's and Google's docs |
| [helpfromsmartcaller.md](helpfromsmartcaller.md) | What we inherit from the upstream project |
| [tried_and_failed.md](tried_and_failed.md) | Approaches that didn't work (not models) |
| [tried_and_implemented.md](tried_and_implemented.md) | Approaches that worked and are in the code |
| [session_handover_2026-10-28.md](session_handover_2026-10-28.md) | Picking up from the latest session |
| [session_handover_2026-10-26.md](session_handover_2026-10-26.md) | The first session |

## One-line architecture
```
Phone ──Bluetooth HFP──▶ Raspberry Pi (PipeWire, 16 kHz mono)
   ▶ webrtcvad endpointing ▶ Gnani Prisma STT (streaming WS)
   ▶ Gemini (streamed, with the shop's stock list) ▶ Gnani Timbre TTS (streaming WS)
   ▶ back over Bluetooth          …and at hang-up: orders/<call_id>.json + .txt
```
