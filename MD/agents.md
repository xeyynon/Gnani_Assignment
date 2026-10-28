# Agents

Two kinds: the **pipeline agents** that run a call, and the **AI coding agents** (Claude) that build the project.

## 1. The pipeline agents
Each one is a thread in `ai_caller_final3.py`. They talk only through queues and events, never by calling each other.

| Agent | Watches | Does | Hands off to |
|---|---|---|---|
| watchdog | Bluetooth nodes (`wpctl status`) | Detects call start and end; bumps `_call_gen`; greeting; resets history. Planned: writes the order summary at hang-up | Everyone, through `_call_gen` |
| recorder | The mic (`pw-record`, 30 ms frames) | VAD, onset confirmation, streams audio to STT, decides when the caller stopped. Also detects barge-in during playback | processor (`audio_q`) |
| processor | `audio_q` | Filters, language lock, the LLM turn, reply checks, streaming TTS. Planned: number normaliser, order state | playback (`reply_q`) |
| playback | `reply_q` | Plays audio (`pw-play`), mutes the echo tail, opens the barge-in window between sentences | — |
| loopback_guard | PipeWire links | Cuts the echo loopback WirePlumber keeps recreating | — |
| vad_metrics_writer | `_vad_metrics_q` | Writes VAD metrics to CSV off the hot path | — |

The models they call (Prisma, Gemini, Timbre) are in [ml.md](ml.md), and the step-by-step flow is in [flow.md](flow.md).

## 2. Notes for AI coding agents
For Claude (or any coding agent) working in this repo. The root [CLAUDE.md](../CLAUDE.md) is the build brief; this section is how to work.

### Before you start
1. Read [DukaanDost_MASTER.md](DukaanDost_MASTER.md) for the status, then [tasks.md](tasks.md) and [../CHANGELOG.md](../CHANGELOG.md).
2. Read the newest `session_handover_*.md`.
3. Read [rules.md](rules.md). R-2, R-3 and R-5 aren't negotiable.
4. Before "fixing" something that looks odd, search [decisions.md](decisions.md), [tried_and_failed.md](tried_and_failed.md) and [failmlmodel.md](failmlmodel.md). It's probably deliberate.

### The codebase in brief
- `ai_caller_final3.py` is ~3,400 lines with long, deliberate comments that explain *why*. Read the comment above a setting before changing it.
- The Pi is the real runtime: Bluetooth, PipeWire, `wpctl`, `pw-record`, `pw-play`. On Windows you can run module-level tests (STT, TTS, normaliser, conversation manager) but not a call.
- `tests/test_streaming_e2e.py` runs the conversation, validator and TTS path without a call. Use it as the model for offline tests.

### Working rules
- **Smoke test before integrating.** Prove each Gnani API works in a standalone script first.
- **Verify vendor facts against the live docs** (docs.gnani.ai). The facts in [external_research.md](external_research.md) were read on 2026-10-26 and may have changed.
- **Don't guess limits.** Upstream lost days guessing Sarvam's concurrency limit before reading the docs.
- **Measure, then write the number down** with a date and a source.
- **Update the MD files** that your change touches, in the same change.
- **Don't run git commit or push** unless asked.
- **No client names.** If you find one in this repo, flag it.

### Versioning
Label every commit a build or an InBul, and follow the flow in [project_docs_guide.md](project_docs_guide.md). Batch builds (about 10 fixes each). Never hand-edit `CHANGELOG.md`.

### Ending a session
Write `MD/session_handover_<YYYY-MM-DD>.md`: what changed (with build and InBul ids), what's verified and how, what's half-done, and what to do next. Update the status table in [DukaanDost_MASTER.md](DukaanDost_MASTER.md).
