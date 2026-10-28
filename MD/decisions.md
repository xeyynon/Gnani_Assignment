# Decisions

Every design decision gets an id, `DEC-NNN`, numbered in the order it's recorded and never reused. Each entry says what we decided, why, and what would make us revisit it. DEC-009 to DEC-019 came with the upstream codebase. They were made on real calls, so keep them unless there's new evidence.

This file says **why**. What changed, and when, is in the build reports (`MD/builds/`) and the InBul commits.

**Latest: DEC-030.**

## Dukaan Dost decisions
### DEC-001 · Build on the earlier voice-agent codebase (2026-10-26)
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

**Update 2026-10-28:** largely overtaken by DEC-023. Prisma v3.0 hears the language itself, so neither option is needed for STT. The open part is only the **greeting's language**: it's spoken before the caller says anything. Plan: greet in Hinglish ("Namaste! Dukaan Dost mein aapka swagat hai…") with one line in Telugu, then follow `detected_language_code`.

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
| DEC-015 | Log to `dukaan_dost.log` (rotating), and send the background process's stdout to `/dev/null` | `/tmp` on the Pi is RAM-backed; the old `/tmp` log grew without limit |
| DEC-016 | `setsid nohup … < /dev/null &` to run in the background | Plain `&` or piping through `tee` let the shell signal the process |
| DEC-017 | Keep `google-cloud-aiplatform` in requirements | The Vertex path needs it, even with no direct import (checked with `pip show`) |
| DEC-018 | Flush the first sentence early at its first comma | Starts TTS sooner. The split clip plays back to back, with no barge-in gap |
| DEC-019 | Multi-line telephony parked | No need for it. Cheapest fallback: another phone and Pi per line |

## Decisions recorded on 2026-10-28
### DEC-020 · The baseline codebase is Build 1000 (2026-10-28)
The first commit is the inherited agent, already de-identified, as **Build 1000**. It behaves on a call exactly like upstream: Sarvam STT, Gemini on Vertex, Google TTS. **Why:** it's a working, user-visible agent, and starting the numbering there lets every later build report say what changed from a known baseline.

### DEC-021 · The upstream clone stays out of git without being named (2026-10-28)
Moving the clone out of the project folder failed (permission denied, 2026-10-28). Until it's moved, it's excluded through `.git/info/exclude`, which is local and never committed, instead of `.gitignore`, which would put its client-named folder into the repo. **Revisit:** delete the exclude line once the folder is moved.

### DEC-022 · CLAUDE.md stays untracked until the client name is out of it (2026-10-28; resolved the same day, InBul10: rewritten without it and tracked)
The brief names the client twice (in a path and in a "don'ts" line). Committing it would write the name into git history for good. It stays untracked until it's rewritten. **Revisit:** when CLAUDE.md is reworked.

## Decisions recorded on 2026-10-28 (after the docs research)
### DEC-023 · Prisma v3.0, with a language list, as the STT model (2026-10-28)
Use `x-model: prisma-v3.0` with `lang_code: hi-IN,en-IN,te-IN`, and feed `detected_language_code` into the existing language lock. v3.0 shipped on 2026-10-22: it identifies the language itself (a list is a hint, not a lock), handles code-mixed speech (`codemix` format), takes up to 200 product names and phrases as `x-keyterms`, and has a `commit` frame that ends an utterance immediately.
- **Why a list, not `indic-auto`:** Gnani says listing the likely languages "helps most with short clips". Order turns are short ("haan", "do kilo"), and we only support these three.
- **Why it fits the existing code:** our recorder already decides when the caller stops (webrtcvad, 650 ms hangover). `finish()` sends `commit` instead of ~600 ms of silence, which saves that time on every turn.
- **Fallback:** Prisma v2.5 with a fixed `lang_code`, behind the same env var, if v3.0 tests worse on our audio. **Revisit:** if the smoke test shows v3.0 mislabelling Telugu or Hinglish.

### DEC-024 · Rely on Timbre's own text normalisation; keep only a thin pre-pass (2026-10-28)
Timbre now normalises numbers, ₹, units, dates and times on every request. We **don't** write a full number-to-words converter. The pre-pass only:
- sets `language` explicitly (`hi-IN` or `te-IN`, never `auto`), because `auto` reads text with no Indic script as English
- writes units the way callers say them ("kilo", "litre"), because Timbre always reads `kg` as the English "kilograms"
- leaves ₹ amounts as digits for Timbre to read

**Why:** less code to break before the demo. **Revisit:** if the smoke test shows Telugu number words wrong; Gnani says Telugu word choices are "under continuous refinement". Then add Telugu-only spelled-out amounts.

### DEC-025 · Gemini model chosen by env var; default to a current model (2026-10-28)
`LLM_MODEL` becomes an env var. The default moves off `gemini-2.5-flash`, which Google now serves only to users who used it before. Candidates are `gemini-3.5-flash-lite` (fastest) and `gemini-3.8-flash`, picked by time to first sentence and order accuracy in the eval. **Why:** a new AI Studio key may be refused 2.5 Flash outright.

### DEC-026 · The entry is kirana orders plus an udhaar (credit) ledger (2026-10-28)
Chosen by Surya from the options in [idea_research.md](idea_research.md). The agent takes phone orders as planned, and also keeps the shop's credit book by phone: it records an order as udhaar when the caller asks, tells a regular customer their outstanding balance, and records a promise to pay.
- **Why:** kirana ordering is one of Gnani's own example ideas, and a competing entry is already public. The credit ledger is how real kiranas run, no visible entry does it, and balance enquiries and promises to pay are what Gnani's collections customers buy.
- **Scope guard:** the ledger is the first thing cut if time runs short. Without it, the entry is still the kirana order agent.
- **Alternatives rejected:** an outbound EMI-reminder caller (outbound dialling from the Pi is too risky for the deadline) and a clinic appointment line (a full re-plan).

### DEC-027 · Dukaan Dost has two call types on one phone line: shop orders and Udyami loan guidance (2026-10-28)
Chosen by Surya from [problem_research.md](problem_research.md). One agent, one number, one pipeline. The agent finds out in the first turn which of two things the caller wants:
1. **Shop orders (with udhaar):** a customer orders from the kirana and can put it on credit (DEC-026).
2. **Udyami Sahayak, loan guidance:** a would-be or new shopkeeper says how much money they can put in and what business they want, and hears the project cost, the maximum loan, the scheme, the interest rate and the instalment, spoken in their language (SIH 2026 PS 26091).

- **Why this mix:** the loan calculator is deterministic (exact right answers, so a clean evaluation) and speaks to Gnani's lending customers. The kirana orders keep the story Gnani already named. The shop is the link: the same shopkeeper who takes orders is the one who might borrow to stock it.
- **Scope order, because two products in 12 days is the risk:**
  1. **Gnani integration** (Prisma, Timbre, Gemini key): needed by everything. Build first.
  2. **Udyami loan guidance:** small and deterministic (three inputs plus a calculator). Build second, so there's a complete, measurable flow early.
  3. **Shop orders:** the stock list, the order state and the order summary.
  4. **Udhaar ledger:** cut first if time runs short.
- **If time runs out:** ship whichever of 2 or 3 is complete and measured, and describe the other as future work. Don't ship two half-built flows.
- **Scheme figures are indicative.** They come from an SIH problem statement, not the scheme documents. The agent says so ("andaaz se"), and the README labels them the same way, until checked against the official scheme documents.

### DEC-028 · Loan instalment assumptions (2026-10-28)
SIH PS 26091 gives the scheme rules (10% margin, 90% loan, two schemes, rates, tenures, moratoria, caps) but **not the instalment formula**. `dukaan_dost/loan_calculator.py` assumes:
- **Monthly reducing-balance instalments (an EMI)** at annual rate ÷ 12. The PS also mentions a "quarterly repayment schedule"; monthly is clearer to say on a phone call, and the code can be extended.
- **Interest accrues during the moratorium and is capitalised** (added to the loan), then the loan is repaid over the remaining months (36−3 = 33 for Micro Finance, 84−6 = 78 for Term Loan). This is the conservative reading: it gives a higher instalment than serving the interest during the moratorium.
- **The loan cap can bind just under the scheme boundary.** At a ₹1.40 lakh project cost, 90% is ₹1,26,000 but the Micro Finance cap is ₹1,25,000, so the caller's own share becomes ₹15,000, not ₹14,000. The calculator reports `own_contribution` and the agent must say it.
- Amounts are rounded to the nearest rupee.

**Every figure is indicative** and the agent says so. **Revisit:** when the official scheme documents are checked (task in [tasks.md](tasks.md)); if they define the instalment differently, change `monthly_instalment()` and its tests.

### DEC-029 · Run without the Raspberry Pi: a transport interface, browser first, phone number as stretch (2026-10-28)
Chosen by Surya from [pi_free_plan.md](pi_free_plan.md). The pipeline takes audio in and out through a small `Transport` interface (`dukaan_dost/transport.py`), selected with `AUDIO_TRANSPORT` (default `pipewire`).
- **Order:** (1) the interface with today's Pi code moved behind it, behaviour unchanged (InBul09); (2) a laptop mic and speaker transport for development; (3) a browser WebSocket transport and page, the Pi-free "call"; (4) re-tune the settings that were set for Bluetooth, one at a time, against the evaluation harness; (5) stretch: a cloud phone number on the same WebSocket transport.
- **Why:** the Pi-specific code was a small, bounded part of the file (call detection, loopback cutting, `pw-play`, `pw-record`, `espeak`); the logic is transport-independent. A browser transport is free and works in days, and without Bluetooth echo it allows real speak-over barge-in. A phone number needs Indian-number paperwork we can't count on in 12 days.
- **Honesty rule:** the README and posts say "browser call" or "simulated phone line" unless a real number is wired up and tested (R-5). The Pi transport stays, as the only one proven on real calls, and as a comparison.
- **Revisit:** if a phone number turns out to be quick to get, move step 5 earlier.

### DEC-030 · Repository layout and naming for a public repo (2026-10-28)
Before the first push, everything named for the earlier project was renamed (InBul10):
- `ai_caller_final3.py` is now the `dukaan_dost/` package: `python -m dukaan_dost` from the project root. The helper modules from `companies/core/` live beside it in the same package, with their file names unchanged.
- `companies/<name>/` is now `shops/<name>/`; `COMPANY_NAME` is now `SHOP_NAME` and defaults to `dukaan_dost`, so no env var is needed.
- The benchmark tools moved to `evaluation/` (run as modules, results in `evaluation/results/`, committed). The old Google-STT diagnostic script was removed (it stays in git history). The two live cloud tests moved to `tests/manual/` and are excluded from the default `pytest` run by `pytest.ini`.
- `AI_CALLER_*` diagnostics are `DUKAAN_*`; the log is `dukaan_dost.log`; the service is `dukaan-dost.service`; the Pi run guide moved to `deploy/RUNNING.md`; the old flow doc is `MD/pipeline_reference.md`; `MD/helpfromsmartcaller.md` became `MD/origin.md` and no longer names the earlier project.
- `CLAUDE.md` was rewritten without any customer name, and is tracked.
- **Why:** the repo is going on GitHub, and it should read as Dukaan Dost, not as a renamed copy of something else. A package under `dukaan_dost/` also removes the `sys.path` games the root-level script needed.
- **Not changed:** git history before this commit still has the earlier names (for example the title of Build 1000). It can be rewritten before the first push if wanted.
