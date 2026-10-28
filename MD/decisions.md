# Decisions

Every design decision gets an id, `DEC-NNN`, numbered in the order it's recorded and never reused. Each entry says what we decided, why, and what would make us revisit it. DEC-009 to DEC-019 came with the upstream codebase. They were made on real calls, so keep them unless there's new evidence.

This file says **why**. What changed, and when, is in the build reports (`MD/builds/`) and the InBul commits.

**Latest: DEC-022.**

## Dukaan Dost decisions
### DEC-001 · Build on the Smart Caller codebase (2026-10-26)
The pipeline (barge-in, VAD, language lock, call isolation) already works on real calls. Rebuilding it would eat the whole deadline. **Revisit:** never, for this contest.

### DEC-002 · Gnani for STT and TTS, Gemini for the LLM (2026-10-26)
The contest needs at least one Gnani model. Evon isn't on the API, so Gemini stays. **Revisit:** if Gnani puts Evon on the API before Nov 5.

### DEC-003 · One Timbre v3.0 voice for every language (2026-10-26)
v3.0 voices cover all 10 languages, so the agent sounds like one person when the caller switches. v2.5 voices are one language each. **Revisit:** if the v3.0 Telugu sounds clearly worse than a v2.5 Telugu voice in the smoke test.

### DEC-004 · Keep the old providers selectable (2026-10-26)
`STT_PROVIDER` and `TTS_PROVIDER` keep `sarvam` and `google`. They give us a baseline for the eval table and a failover. **Revisit:** no.

### DEC-005 · Language selection: open
- **A:** the greeting asks the caller to pick a language. Simple and reliable, but one extra step.
- **B:** start in `hi-IN` (it handles Hinglish), and switch when the caller asks or clearly speaks another language.

Leaning towards **B with an A-style prompt as backup**: start in `hi-IN`, and greet with a line that tells Telugu and English callers they can say "Telugu" or "English". Decide after the smoke test shows how `hi-IN` handles English and Telugu speech.

### DEC-006 · How the order state is updated: open
Structured JSON from Gemini on each turn vs extraction from the transcript at hang-up. See [flow.md](flow.md). Decide before building step 8.

### DEC-007 · Call recording off during the contest (2026-10-26)
Upstream records every call (`CALL_DATA_ENABLED` is on by default) for future training. The contest allows **synthetic data only**, and test calls may involve real people. Default it to off. **Revisit:** never for this repo.

### DEC-008 · Builds and InBuls (2026-10-28)
Versioning follows the scheme in [project_docs_guide.md](project_docs_guide.md):
- a user-visible change ships as **Build N** (from 1000, pinned by the git tag `build-N`, with a report in `MD/builds/`)
- an internal change (docs, scripts, tests) is an **InBulNN** commit with an `InBulNN` tag

Small fixes are batched, about 10 per build. **Why:** the same scheme as our other projects, so history reads the same way everywhere, and the CHANGELOG only lists what a user would notice. This replaces the "DD01" idea from 2026-10-26.

## Decisions inherited from upstream
| ID | Decision | Why |
|---|---|---|
| DEC-009 | **Gap-based barge-in only**; no always-on keyword spotter or AEC | AEC risks reopening Bluetooth echo and stability bugs that were already fixed once. Revisit only on a real complaint about interrupt response |
| DEC-010 | `VAD_HANGOVER_MS=650` (was 500) | Natural pauses over 500 ms chopped one utterance into fragments. A deliberate ~150 ms latency cost per reply |
| DEC-011 | `VAD_ONSET_CONFIRM_FRAMES=2` | A single 30 ms noise spike was opening an STT session. Two frames stays under the 4-frame "stop" check |
| DEC-012 | STT concurrency 10, from the vendor's documented limit | Guessing 1→2→4 failed. Sarvam's real limit is 20 (Starter). **For Gnani, look up the documented limit; don't guess** |
| DEC-013 | Session-sticky language; a bare "hello", "hi" or "hey" doesn't set the lock | "Hello" carries no language signal in India. "Namaste" and "namaskar" **do**, so they're not in the list |
| DEC-014 | Native-script text can re-lock the language mid-call; romanized keywords only affect the current reply | Script is an unambiguous signal; romanized keywords aren't |
| DEC-015 | Log to `ai_caller.log` (rotating), and send the background process's stdout to `/dev/null` | `/tmp` on the Pi is RAM-backed; the old `/tmp` log grew without limit |
| DEC-016 | `setsid nohup … < /dev/null &` to run in the background | Plain `&` or piping through `tee` let the shell signal the process |
| DEC-017 | Keep `google-cloud-aiplatform` in requirements | The Vertex path needs it, even with no direct import (checked with `pip show`) |
| DEC-018 | Flush the first sentence early at its first comma | Starts TTS sooner. The split clip plays back to back, with no barge-in gap |
| DEC-019 | Multi-line telephony parked | No need for it. Cheapest fallback: another phone and Pi per line |

## Decisions recorded on 2026-10-28
### DEC-020 · The baseline codebase is Build 1000 (2026-10-28)
The first commit is the inherited agent, already de-identified, as **Build 1000**. It behaves on a call exactly like upstream: Sarvam STT, Gemini on Vertex, Google TTS. **Why:** it's a working, user-visible agent, and starting the numbering there lets every later build report say what changed from a known baseline.

### DEC-021 · The upstream clone stays out of git without being named (2026-10-28)
Moving the clone out of the project folder failed (permission denied, 2026-10-28). Until it's moved, it's excluded through `.git/info/exclude`, which is local and never committed, instead of `.gitignore`, which would put its client-named folder into the repo. **Revisit:** delete the exclude line once the folder is moved.

### DEC-022 · CLAUDE.md stays untracked until the client name is out of it (2026-10-28)
The brief names the client twice (in a path and in a "don'ts" line). Committing it would write the name into git history for good. It stays untracked until it's rewritten. **Revisit:** when CLAUDE.md is reworked.
