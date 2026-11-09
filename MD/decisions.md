# Decisions

Every design decision gets an id, `DEC-NNN`, numbered in the order it's recorded and never reused. Each entry says what we decided, why, and what would make us revisit it. DEC-009 to DEC-019 came with the upstream codebase. They were made on real calls, so keep them unless there's new evidence.

This file says **why**. What changed, and when, is in the build reports (`MD/builds/`) and the InBul commits.

**Latest: DEC-034.**

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

### DEC-029 · Run without the Raspberry Pi: a transport interface, browser first, phone number as stretch (2026-10-28; the Pi transport it kept was removed by DEC-032)
Chosen by Surya from [transport_plan.md](transport_plan.md). The pipeline takes audio in and out through a small `Transport` interface (`dukaan_dost/transport.py`), selected with `AUDIO_TRANSPORT` (default `pipewire`).
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

### DEC-031 · Python first; Cython only for a measured hotspot (2026-10-28)
Surya's plan: develop in Python, and move to Cython later. Recorded with the evidence so the later step is a decision, not a reflex.
- **Measured on a laptop, not the Pi** (`python -m evaluation.profile_frame_cost`): the work done on every 30 ms frame (energy plus both VAD checks) costs about 0.03 ms, which is 0.1% of the frame. The heaviest function is `_learn_caller_pitch`, about 2.4 ms once per utterance. Even 10× slower on the Pi, per-frame work stays around 1%.
- **So Cython wouldn't make a call feel faster.** What makes a reply slow is waiting: the speech, language-model and text-to-speech network calls, and the 650 ms end-of-speech wait. Those are tuned through the settings and the Gnani integration (DEC-023, [transport_plan.md](transport_plan.md) section 4), not by compiling.
- **When Cython becomes worth it:** a measured hotspot on the target machine, most likely 8 kHz to 16 kHz resampling and mu-law conversion if a phone-number transport is added (`audioop` is gone from newer Python), or pitch learning if the Pi is slow. Try vectorising with numpy first.
- **How, if it happens:** move only that function into its own small module with a plain-Python version that stays the reference. Add the compiled version with the same signature as an *optional* extra, import it with a fallback to the Python one, and add a test that both give the same answers. A compiled build must never be required to run the agent; the Pi would need a C compiler and the Windows laptops a build toolchain.
- **Not done now:** no `.pyx` files, no build step, no new module. Premature until the profile on the Pi shows a hotspot.

### DEC-032 · Software only: the Raspberry Pi and Bluetooth are removed (2026-10-28)
Surya's instruction: remove the Pi dependency completely and make the project software based. Done in Build 1002.
- **What went:** `transport_pipewire.py`, the loopback-cutting thread and its helpers, the `deploy/` folder (Pi install script, systemd unit, run guides), and the Pi/Bluetooth wording in the docs. `webrtcvad-wheels` replaces `webrtcvad` so installs work on Windows, macOS and Linux.
- **What replaced it:** `transport_websocket.py` and `dukaan_dost/web/index.html`. `python -m dukaan_dost` serves a call page; a browser tab is the caller. The audio protocol is documented in [transport_plan.md](transport_plan.md). The `Transport` interface stays, so a phone-number transport or an offline replay transport can be added.
- **What we give up:** the "answers a real phone call" claim. The README, videos and posts say "browser call" and call phone-line audio "simulated" unless a real number is wired up and tested (R-5). The Pi transport was also the only one proven on real calls; the browser one has only been tested offline so far (B-08).
- **What we gain:** it runs from one command on any laptop, anyone can try it, the tests exercise a real transport, and the browser's echo cancellation removes the main reason for the long mic mute (to be tuned with measurements).
- **Revisit:** a phone-number transport, if a provider's paperwork turns out to be quick (DEC-029 stretch).

### DEC-033 · CI/CD with GitHub Actions: checks on every push, a release and an image per build tag (2026-10-28)
Details in [ci_cd.md](ci_cd.md).
- **CI** runs the offline tests on Linux (Python 3.10 and 3.12) and Windows (3.12), a ruff check for real errors only, repo checks (secrets, local-only files, banned names, commit titles, doc links), the call page's Node tests, and a container build. No keys are needed.
- **CD** is a GitHub Release (notes from the build report) plus a container image, on `build-*` tags only. **No auto-deploy**: there is no server, and the agent runs locally or from the image.
- **Banned names live in a repository variable**, never in a committed file, because the list itself would be the thing we must not commit (R-3).
- **Lint is deliberately narrow** (syntax errors and undefined names). The code base has long explanatory comments and a history of style choices, so wide style rules would bury real errors.
- **Not yet proven on GitHub.** The first run may need fixes (B-10).

### DEC-034 · Dashboards: shopkeeper first, many shops per agent, one admin password plus a PIN per shop (2026-10-28)
Surya asked for two dashboards: an **admin** dashboard (oversee everything, add shops, fix their errors) and a **shopkeeper** dashboard. Chosen order: shopkeeper first, then admin. Chosen shape: the call link picks the shop, and sign-in is one admin password plus a PIN per shop.
- **Many shops, one agent.** The call link is `/s/<shop>/` and a call arrives on `/s/<shop>/ws`; `/` and `/ws` are the default shop. Each call loads that shop's prompt, knowledge and greeting (`_active_shop`, `_get_conv_mgr`). One call at a time still holds across all shops.
- **Sign-in.** HTTP Basic auth: the shop's PIN as the password (any user name), or user `admin` with `ADMIN_PASSWORD`. PINs are stored hashed (scrypt) in `data/auth.json` (gitignored). A shop with no PIN can't be opened. Five wrong guesses lock that shop for that address for a minute. Basic auth is only safe over `localhost` or `https`.
- **Data contract.** Plain JSON under `orders/<shop>/` (`order_<id>.json`, `loan_<id>.json`, `ledger.json`), documented in `store.py`. The agent will write them; the dashboards read them. Files that can't be read are reported, never fatal.
- **Read-only first.** The shopkeeper dashboard is `GET` only and polls `/s/<shop>/dashboard/data` every 3 seconds. The page builds everything from text nodes (order data contains caller-chosen text) and runs under a strict content security policy.
- **The admin dashboard needs writes** (add a shop, resolve an error). The server's HTTP layer can't read request bodies, so the plan is to drive the admin page over a WebSocket with JSON commands, which needs no new dependency. Not built yet.
- **Not built:** the agent doesn't write orders yet (DEC-027 build steps 7 and 8), so until it does the dashboard shows only demo data (`python -m dukaan_dost.demo_data <shop>`), clearly marked as made up (B-11).
- **Risk to the schedule:** the dashboards and multi-shop support compete with the Gnani integration and the evaluation, which is what the contest judges.

### DEC-035 · Gnani speech backends: how they are built (2026-11-02)
`stt_gnani.py`, `tts_gnani.py` and `tts_provider.py` follow the same interfaces as the Sarvam and Google backends, selected by `STT_PROVIDER=gnani` and `TTS_PROVIDER=gnani`. Choices, each made from the live docs (read 2026-11-02) and the research in `research_papers.md`:
- **One WebSocket per utterance (STT), one per sentence (TTS).** The app does its own end-of-speech detection and hands over one utterance at a time, as it did for Sarvam. Simple, and a failed connection can't poison the next turn. Cost: a handshake each time (B-14).
- **Both header spellings are sent.** The docs disagree with themselves on the names; the WebSocket page says the new name wins when both are sent, so sending both is safe.
- **Audio pacing.** Frames are exactly 1,024 bytes and sent no faster than real time, except a 0.5 s head start for the recorder's pre-roll (`GNANI_STT_BURST_ALLOWANCE_SEC`), because the docs warn that sustained bursts hurt the server's voice detection.
- **End of utterance = `commit` plus 0.6 s of trailing silence.** `commit` is documented on the WebSocket page; the silence is a fallback if a server ignores it. Done when every segment the server started has produced its transcript and a short grace (0.3 s) has passed with nothing new.
- **Language.** No language given: Prisma gets the hint list `hi-IN,en-IN,te-IN` and reports `detected_language_code`. A language given (the app's per-call lock): that one code only. Results tagged with a language the deployment doesn't serve are dropped as noise, as with Sarvam.
- **TTS over the WebSocket, not REST.** `synthesize()` collects the same stream and wraps it in a 16 kHz WAV, so there is one tested path. It retries once.
- **Speech text.** `normalize_text()` only handles rupee amounts and Indian digit grouping. Spelling digits as words in Hindi and Telugu is deliberately not built until E2 shows whether Timbre v3.0 needs it (DEC-024).
- **Keyterms** come from `set_keyterms()`, ASCII only (HTTP headers), capped at 200. Hindi/Telugu script product names can't be boosted this way.
- **Concurrency.** A semaphore, default 4 sessions, until experiment E5 measures the account's real cap.
- **Not proven.** Everything above is checked against stand-in servers only (B-13).

### DEC-036 · The shop's stock list is `stock.json`; everything else is generated from it (2026-11-02)
`shops/<name>/stock.json` is the one source of truth for what a shop sells: SKU, English/Hindi/Telugu names, Latin-script aliases, unit, pack, price, in-stock. `scripts/build_shop_knowledge.py` writes `knowledge/products_pricing.md` from it (one `##` section per item, names in all three scripts so retrieval finds it in any language; an out-of-stock item says so in the text) and a test fails if the generated file is stale. The same file gives the Prisma keyterms (Latin-script names first, then aliases, capped at 200) and will be what the code checks every spoken item against (research method M4).
- 61 items, two out of stock (paneer, mosquito coil) so that case can be tested.
- **Prisma key terms are the 61 main English names only** (amended 2026-11-02, see DEC-038). The Latin-script aliases are used for finding the item in the knowledge file, not for boosting speech.
- Prices are made up. Brand names (Amul, Maggi, Parle-G, Good Day) are real, as the project brief suggested, with made-up prices.
- Hindi and Telugu names are unchecked (B-16).
- The prompt's totals are interim (B-15).

### DEC-037 · Take three small fixes from the research before building the order flow (2026-11-02)
Reading the code against `research_papers.md` found three real defects, fixed now because each is small and affects every call: the reply splitter (B-17, method M1), the history after an interruption (B-18, method M2) and Hindi/Telugu keyword retrieval (B-19, found while writing the shop content). The bigger research method, the rule layer (M4), is the order flow itself and waits for Step 8.

### DEC-038 · Groq is the language model for now; the model writes digits, Timbre says the words (2026-11-02)
Surya had no Gemini key and asked to use Groq for now. `llm_groq.py` and `llm_provider.py` switch the language model with `LLM_PROVIDER=groq|gemini` (default gemini; `.env` sets groq). Gnani has no public LLM, so the language model is not a Gnani one either way; the Gnani models in the pipeline are Prisma and Timbre.
- **Model: `qwen/qwen3.8-27b`.** Checked with `GET /models` on this account: the Llama models in Groq's docs are not available to it. gpt-oss reasons first and can return an empty reply on a small token budget. Qwen answered directly: 300 to 900 ms to the first sentence in an informal run (not saved, not for the README). It is a preview model (B-20).
- **Digits, not number words.** The model spelled Telugu and Hindi numbers wrongly ("ఛార్టీ రూపాయలు", "chhappin" for 165). Timbre reads digits correctly: Hindi, Telugu, Hinglish and English sentences with amounts such as 120, 165, 285 and 1,250 were spoken and heard back by Prisma as the same numbers. So the shop prompt tells the model to write every amount as digits, and Timbre says them. This answers DEC-024's open question: no Hindi/Telugu number-to-words pre-pass is needed for amounts. Totals are still the model's addition until the rule layer exists (B-15); in the informal run they were right (88+165+14=267, 120+165=285).
- **Key terms.** 200 terms including Latin aliases made things worse on the real service (see `stock.keyterms`); the 61 main names fixed "Maggi" and "Amul" with no harm. Six sentences only: the evaluation repeats it.
- Rate limits shape the evaluation (B-20).

### DEC-039 · The order flow: the model reads the order, the code does the money (2026-11-02)
Research method M4 (research_papers.md) built as `order_session.py` and `order_turn.py`; closes B-15 (totals added by the model), B-11 (the dashboard had only demo data) and B-02 (long orders forgotten). How a turn works:
- **The model answers with one JSON object**, not free text: `ops` (add / set / remove with a SKU and a quantity), `payment`, `customer_name`, `delivery`, `finish` (the caller said that is all) and `say` (a short reply). Groq's JSON mode and Gemini's JSON mime type both support it (`ask_json`). The reply is no longer streamed from the model; Groq is fast enough that the first sentence still starts within about a second.
- **The code applies it** to an `OrderSession`: unknown items and items out of stock are refused, quantities must make sense for the unit (kg and litre in steps of 0.25 up to 25, everything else whole numbers up to 24), each line is price x quantity rounded to whole rupees half up, the total is the sum of the rounded lines.
- **The code speaks on every turn that touches the order** (amended the same evening, after trying the real model). On a turn where items were added, changed, removed or refused, the caller said that is all, a price was asked, or payment was chosen, the code says all of it: the changes with prices and the running total, the read-back, and a fixed follow-up question ("Anything else?" / "How would you like to pay: cash, UPI or credit?") in the caller's language, using the stock list's own names in English, Hindi or Telugu. **The model's own words are not used on those turns.** Reason: on the real model they narrated each change a second time with totals of their own that disagreed with the code's (209 and 221 spoken beside the correct 265), invented a delivery time and an address, a ghee price and brands, and slipped into English during Hindi calls. The model's words are used only when nothing about the order happened (a greeting, a question about the shop's hours). `say` may carry `[LINES]` and `[ORDER]` for those turns (square brackets: with curly braces the model once answered with the bare text `{ORDER}`).
- **Things the shop does not sell** are named by the model in `not_sold` (the caller's own words) and the code tells the caller ("Sorry, we do not have dragon fruit."), in their language; without this an unlisted item vanished silently from a longer request. The instructions also say: one op for every item named, even when another item in the same message cannot be sold, and list the Hindi and Telugu number words ("do" is two).
- **Prices come from the stock list.** The model puts the SKUs the caller asked about in `price_of`; the code says "Sugar is 44 rupees per kilo." It is told never to write a price.
- **The closing sentence is the shop's.** When the caller has just chosen how to pay, the code says a fixed sentence from `config.yaml` (`order_closing`, `order_closing_credit`, in en/hi/te), for example the delivery time, instead of the model's words.
- **The model is shown the order so far** (items and quantities, no amounts), so it does not need long history. `LLM_HISTORY` stays at 3.
- **The answer's shape is forced** with a strict JSON schema (`order_turn.SCHEMA`) where the service supports it, falling back to plain JSON mode. If the model still answers in plain words, Groq refuses it in JSON mode but returns the text; the conversation manager asks once more with a reminder, and speaks the fallback message if that fails too. Plain words are never spoken, because they can disagree with the order.
- **The order file** is written when the call ends (`order_<id>.json` for the dashboard, `.txt` readable), or at shutdown, or when the next call starts if the end was missed. Status: `confirmed` once cash or UPI is chosen, `credit_pending` for udhaar, `incomplete` otherwise. Nothing is written if nothing was ordered. The call page gets an `order` event after each change.
- **Not built:** the udhaar balance and limit check (Step 8b; udhaar orders are saved as `credit_pending` with no balance), choosing alternatives for out-of-stock items in code (B-21).
- **Model.** The default Groq model became `openai/gpt-oss-20b` (amended DEC-038): across 11 real calls it produced valid JSON every time, where the Qwen preview model returned broken fragments ('{done', '{"opts') on about a quarter of turns, even with a schema. gpt-oss reasons first, so it is given room (`max_tokens` at least 500 for it). It misread a quantity once ("do kilo" as 1), hence the number-word list in the instructions.
- **Knowledge search.** Everyday words (the, of, is, what, kya, hai) no longer count when picking sections, and a match in an item's name outweighs one in its body, so "what is the price of ghee?" finds the ghee section first (it had been missed, and the model said the shop had no ghee).
- **Cost:** an order turn is about 2,000 tokens, so about four turns a minute on this Groq account (B-20). A failed first answer doubles that for that turn.

### DEC-040 · The web pages are built from components, stitched in when the page is served (2026-11-02)
Surya builds interfaces component by component (atoms, molecules, organisms, pages), and the two pages did not: each was one 500-line file, and the tokens, the theme button, the brand block, the DOM builder, the formatters and the key check were each written twice and could drift.
- **Chosen:** components are small files under `dukaan_dost/web/components/`; a page is a template of `{{include:path}}` lines; `dukaan_dost/webpage.py` composes them on every request. Chosen over shared asset files because each page stays one self-contained response, so the dashboard's content security policy (no outside files) and the offline tests do not change.
- **Safety:** an include can only name a file inside the components folder (`..` and absolute paths are refused); includes nest to a small depth, which also stops a component including itself; a missing component is an error, not a gap.
- **Enforced by tests, not by care:** every component is used by a page, every include resolves, no component carries its own tag, and no colour is written outside the tokens (the colour test was seen to fail when a stray colour went into each kind of component).
- **Cost:** two renders are now composed at request time (a few small file reads; fine at this scale), and the Node page tests ask Python to compose the page (`tests/web/composed.mjs`) so there is one implementation of the rules.
- **Not done:** a build step, a framework, or separate asset files. Revisit if the pages grow past what one response should carry.

### DEC-041 · One recipe for bento, glass, brutalist accents and minimalism (2026-11-02)
Surya asked to mix bento 2.0, glassmorphism, brutalism and minimalism. Used together they conflict (glass wants softness, brutalism wants hard edges), so each got one job: bento is the layout, glass is the chrome, brutalism is an accent on the one action and one figure that matter, minimalism is the base.
- **Glass only on chrome, never on figures.** A blurred background under a number costs legibility, and an earlier project's experience was that glass looks wrong over busy content. Cards that carry numbers stay solid. Opaque fallbacks for no `backdrop-filter` and for `prefers-reduced-transparency`.
- **The soft colour blobs behind the glass are a gradient**, which the earlier design rules avoided; they are the one exception, because glass has nothing to show without something behind it. They are tokens, low in contrast, and fixed behind the page.
- **Brutalism limited to the call button, End call and the hero figure,** so it reads as emphasis and not as the style of the whole page.
- **Cost:** the dashboard and call page layouts were restructured (the old column wrappers dissolve into one grid). Numbers are monospace, which falls back to Consolas or Menlo when IBM Plex Mono is not installed (nothing is loaded from outside).
- **Not tried:** a Light/Dark-specific blob set tuned on a real phone screen, or contrast measured with a tool; checked by eye in screenshots at 1280, 1100, 390 and 360 px in both themes.
- **"Needs you" is not a tile (2026-11-02).** It was a narrow pink fourth tile that did not match its neighbours and repeated the "Needs your attention" panel directly below it. Removed; its count is a badge in that panel's heading. Restore it only if a shopkeeper asks for the number without the list.

### DEC-042 · The admin dashboard: a health check per shop, then the writes (2026-11-02, 2026-11-03)
Built on the branch `admin-dashboard`, following DEC-034 (one admin password, writes later over a WebSocket).
- **Read-only first, then the writes (2026-11-03).** The overview and problem list came first; then add a shop, set a PIN, edit the instructions and the stock list, and mark warnings solved, all over a WebSocket with JSON commands (the HTTP layer cannot read request bodies). Every change is its own function in `admin_actions.py`, tested on a temporary folder.
- **A shop's PIN never opens it.** The page shows every shop, so only `admin` with `ADMIN_PASSWORD` is accepted, whatever user name a PIN is sent with. No password set means the route is off (503), never open; the example placeholder counts as not set.
- **Health is checked from files, the way an operator would** (`shop_health.py`), not by asking the agent: config, prompt, English fallback, knowledge, stock, PIN, unreadable order files. Errors mean the agent cannot serve the shop properly; warnings mean it works but something is missing. Nothing is invented: a shop with no orders shows zeros and "no orders yet".
- **"Failed turns" are not in the problem list yet.** The plan listed errors per shop including failed turns; the agent does not record them anywhere yet, and a list built from guesses would be worse than none. Needs the agent to write an error log first.
- **Shared components.** The admin reuses the shop dashboard's frame, menu, top bar, tiles, pills, lists and polling, which were moved from `components/dashboard/` to `components/shared/` (DEC-040); the dashboard's composed page was compared before and after and differs only in the lines that were generalised.
- **`shops.list_folders()`** exists because `list_shops()` hides a folder whose `config.yaml` is missing, which is exactly the shop the admin must show.

- **Writes are all-or-nothing and never destructive (2026-11-03).** A new shop is built in a hidden folder and renamed into place, an existing shop is never overwritten, the stock list is validated as a whole before it is written, `config.yaml` is copied to `.bak` before it is rewritten, and no admin action deletes anything from disk. Removing a shop is deliberately not an admin action.
- **The socket's sign-in.** A WebSocket cannot send the browser's cached password the way a page request does, so the page fetches a ten minute random token with a signed-in request and sends it first. The socket also checks the Origin header, which is what stops a page on another site from using a signed-in operator's browser (cross-site WebSocket hijacking). Commands are limited to 60 a minute.
- **Errors cannot be marked solved, warnings can.** Marking an unreadable config "solved" would be a lie the page tells; a missing PIN the operator has decided to live with is a decision.
- **The activity log** (`data/admin_log.jsonl`, gitignored with the rest of `data/`) records what was done to which shop and when, and never a PIN, a prompt or other typed text beyond a short note on a solved problem.
- **Money is not on the admin page.** Sales and credit totals were first shown and then removed: the admin looks after whether the system works, and a shop's sales belong to its shopkeeper.
- **A running agent picks changes up on the next call:** the admin tells the agent to drop its cached copy of the shop (`_forget_shop`); a call in progress is not disturbed.

### DEC-048 · The evaluation runs the whole agent through a scripted caller (2026-11-03; first numbered DEC-040 by mistake, which was already the components decision)
`transport_replay.py` is a third transport (`AUDIO_TRANSPORT=replay`, `REPLAY_PLAN=<plan>`): a script plays prepared speech into the real pipeline at real-time pace, with silence or generated noise between turns, plays the agent's replies in real time too (so its listening gaps and interruption handling behave as on a call), and records for every turn when the caller stopped speaking, when the first audio of the reply began, what the speech recogniser heard and what the agent said. `evaluation/run_calls.py` makes the speech with Timbre, writes the plan, starts `python -m dukaan_dost` with orders going to a separate folder (`ORDERS_DIR`, `ORDER_SYNTHETIC=1`), waits for the script to finish and saves the raw result. `evaluation/score_calls.py` matches each call to the order the agent wrote and scores it against the expected order of the script.
- **What it measures:** order accuracy (exact items and quantities, with a 95% Wilson interval), item recall and precision, payment, totals against the stock-list arithmetic, time to first audio from the caller's last sample, WER raw and number-normalised, calls with no reply.
- **What it does not:** real voices, real phone lines, echo of the agent's voice into the microphone (the browser cancels it; replay has none), T-WER, the cut-off rate. All speech is Timbre's, so results are optimistic.
- **Pace:** one turn at least 22 s after the previous (`--min-turn-sec`), to stay under Groq's 8,000 tokens a minute; 20 calls (65 turns) take about 27 minutes.
- **Noise:** generated (hiss, rumble, hum), mixed into the microphone for the whole call at a chosen SNR measured against the speech (`--noise 10`).

### DEC-041 · A shorter prompt for order turns (2026-11-03)
Order turns now use a short persona (`order_system_prompt` in `config.yaml`, about 500 characters instead of 2,400) and compact order instructions (about 2,500 characters instead of 5,000, with four examples). Total system text per turn fell from about 9,600 to 5,600 characters. Reasons: Groq's daily token limit (B-33) and time to first audio (B-31). Every rule the real runs had taught is kept: JSON only; ops from the caller's last message only; one op per item named; number words; out-of-stock items still get an op; unsold items go in `not_sold`; prices only via `price_of`. If accuracy drops, the evaluation will show it and this is the first thing to revisit.

### DEC-042 · Order turns send the whole catalogue instead of searching for products (2026-11-03)
The first valid evaluation (B-34) showed that most wrong orders came from the model not being shown the product, not from the model misunderstanding. Keyword search over Hindi, Telugu and Hinglish is brittle (spelling variants, plurals, a limited character budget, mis-heard words). With 61 items the whole list fits: `stock.catalogue_text()` gives one line each, "SKU | English | Hindi | Telugu | unit", plus "OUT OF STOCK", about 3,400 characters, and the model matches by meaning. The knowledge search is kept for shop facts only (delivery, payment, hours) and no longer includes the product file on order turns. Cost: about 3,200 tokens a turn instead of about 2,000, which makes one full run use nearly a whole day of one model's limit (B-33). That limits how many evaluation runs fit before the deadline, so runs are planned: the catalogue run on gpt-oss-20b once its quota recovers (about 16:00 on Nov 3), the noisy run on gpt-oss-120b the next morning. A larger shop (hundreds of items) would need retrieval again, with better matching.

### DEC-043 · A product search that offers candidates, and three catalogue modes (2026-11-03)
`dukaan_dost/product_search.py` matches a caller's words to products by overlapping 2 to 4 letter pieces against each name and spelling separately (cleaning first: no dot under Devanagari letters, no joiners, no full stops, no quantities or unit words), over runs of 1 to 3 words so that a sentence with several products does not dilute any. Pure Python, about 3 ms for 61 items, no model and no network. On 76 phrases (23 real Prisma outputs, 28 variants, 24 held out) its top 8 found 133 of 133 asked-for items, against 0.895 for the keyword search. It also returns false matches (a sentence with no product can score 0.5), so it is only ever used to choose which catalogue lines to show the model, never to add anything to an order. `ORDER_CATALOGUE=full|search|auto` chooses between every item (small shops, default while the catalogue is under 6,000 characters) and the best 12 plus what is already ordered (large shops). Embeddings were considered and left out (no key, heavy dependencies; see `MD/rag_plan.md` section 7). The end-to-end effect of search mode on order accuracy is not measured yet.

### DEC-044 · Loan guidance on the call: keyword routing, code-only figures, lakh words (2026-11-03)
`loan_session.py`, `loan_turn.py` and a `_loan_turn` in the conversation manager connect the loan calculator (DEC-027, DEC-028) to the voice agent, on the same principle as orders: the model only reads, the code decides and speaks.
- **Routing in code.** A keyword check (`loan_turn.detect`) in English, Hindi, Telugu and Hinglish starts loan mode; it costs no tokens and a miss falls back to the order flow. Loan mode is sticky for the rest of the call (later turns such as "I have one lakh" carry no loan word). Telugu అప్పు is excluded on purpose: in a shop it means credit.
- **A short model prompt** (no catalogue, about 1,000 tokens) returns the amount in rupees, whether it is the caller's own money or the whole project cost, the business and the place. If the kind is unclear the code asks ("is that your own money, or the whole project cost?").
- **All figures and sentences come from the code.** The reply reads the amount back ("I heard 1 lakh as your own money, so a project of about 10 lakh"), gives the scheme, the maximum loan, the rate, the grace period, the instalment and the number of months, states the caller's own share when the cap binds, and says the figures are approximate. A correction replaces the quote. The model's own words are used only for a digit-free question about the schemes; any digit in them is dropped.
- **Timbre misreads six- and seven-digit numbers in Hindi and Telugu** (found 2026-11-03 by speaking sentences and reading them back with Prisma): "100000" came back as ten million and "4500000" as 45 million. "1 लाख", "45 లక్షల" and "45 lakh" all came back right. So any amount of one lakh or more is spoken in lakh and crore words (`spoken_amount`); only amounts under one lakh are plain digits.
- **Record:** `orders/<shop>/loan_<id>.json`, shown by the dashboard, written when the call ends.
- **Checked live** (gpt-oss-20b, 7 turns, 2026-11-03): "डेढ़ लाख", "యాభై వేలు", "twelve lakh" and "paanch lakh" were all read correctly and produced the calculator's figures. Four scripted loan calls with expected quotes are in `evaluation/scripts/credit_loans.json`; the scorer checks project cost, loan and instalment. Not yet run as a scored run (token quota).
- **Still open:** the scheme figures come from an SIH problem statement and the instalment rule is an assumption (DEC-028); the call page has no loan panel yet (the UI session can add one; the agent sends no loan event).

### DEC-045 · The udhaar credit book: the code keeps the balance (2026-11-03)
`credit.py` and `shops/<shop>/customers.json` (15 made-up customers with a limit and an opening balance; names in English, Hindi and Telugu) give the shop a credit book over `orders/<shop>/ledger.json`, the file the dashboard already reads.
- **A name is matched by letter overlap in whichever script it was said**, with honorifics removed in all three scripts (ji, bhai, garu, అక్క, जी). A match needs similarity of at least 0.80 and a lead of 0.10 over the next customer; a close call is treated as unknown. A wrong person's debt is worse than a pending one.
- **Flow (all decided by code).** Credit chosen with no name: the code asks for the name. Known and within the limit: the code says the balance, this order and the new balance, the order is saved as `confirmed` with `balance_before` and `balance_after`, and the ledger is updated when the call ends. Over the limit: the code says so, the payment is cleared and the caller picks cash or UPI. Unknown name: saved as `credit_pending` for the shopkeeper. Adding items later re-checks the limit. A balance question ("how much do I owe?") sets a flag and the name; the code reads the balance from the ledger.
- **Settlement at hang-up re-checks the limit** against the ledger as it is then (another call may have used credit since); if it no longer fits, or the ledger cannot be written, the order is kept as `credit_pending` and nothing is charged. The ledger is seeded from the customer list once and never reset.
- **Shops without a customer list** keep the old behaviour (credit means pending).
- **Cost:** one more boolean in the model's note (about 100 tokens a turn).
- **Not built:** promise-to-pay dates, reminders, outbound calls (out of scope, DEC-026).
- **Live check:** partly done (2026-11-03). On the real model "udhaar pe dena" led to the agent asking for the name; the rest of the planned live run (approve, over limit, balance enquiry) was cut off by the model's daily token limit and is still to do. Four scripted credit calls are in `evaluation/scripts/credit_loans.json`.

### DEC-046 · A phone number: a telephony transport built against a stand-in provider (2026-11-03)
`transport_telephony.py` (`AUDIO_TRANSPORT=telephony`) lets a telephony provider's media stream be the call. It subclasses the browser transport, so the server, the one-call-at-a-time session and everything above the `Transport` interface are unchanged; a browser can still call the same server.
- **Two adapters** translate the providers' WebSocket messages (read from their documentation on 2026-11-03): Twilio Media Streams (base64 mu-law 8 kHz; `media`, `mark`, `clear`) at `/telephony/twilio`, and Exotel Voicebot (base64 PCM 8, 16 or 24 kHz; chunks of 3,200 to 100,000 bytes in multiples of 320) at `/telephony/exotel?sample-rate=16000`.
- **Audio conversion is plain numpy** (mu-law, linear resampling). No neural restoration: it made Hindi recognition worse in the papers (M8). `audioop` is not used because Python 3.13 removed it.
- **Playback waits for the provider's `mark`** that follows the clip, the phone twin of the browser's "played" message; barge-in sends `clear`.
- **Sign-in fails closed.** A shared secret, `TELEPHONY_TOKEN` (at least 16 characters), is compared in constant time; with none set every phone call is refused and a warning is logged at start. It comes from the start message's custom parameters (Twilio does not allow a query string on the stream URL) or the URL query.
- **Privacy.** The caller's number arrives in the start message and is never stored or logged (a test checks this). The token is never logged either.
- **One call at a time still.** A second call is closed with 1013 (busy). Several callers at once would need the per-call state in `app.py` made per-call (the rewrite stays future work, see the plan, item 4b).
- **Self-echo filter off by default** on this transport (B-36); `SELF_ECHO_FILTER=1` turns it on.
- **Not tested against a real provider.** Both providers gate streaming behind KYC with no published turnaround (B-39). 31 tests drive a stand-in provider over a real local socket: codecs, both protocols, authorisation failures, busy line, marks, timeouts, barge-in, hang-up, the browser still working.
- **Gnani limit measured** (2026-11-03): 8 Prisma sessions open at once, none refused (`gnani_smoke_test.py concurrency --max 8`). Higher counts untested.

### DEC-047 · A spare Timbre connection, a loan event for the call page, and two more measures in the scorer (2026-11-03)
- **Spare connection (`tts_gnani.py`).** Every sentence opened its own connection, which cost 375 to 420 ms of TLS and WebSocket set-up before the request. One connection is now opened ahead of time on a shared background event loop; the next sentence takes it, and a new one starts opening at once. A socket is still used for exactly one request (the service says one at a time, and the earlier rule that sentences never share a socket stays). A spare older than 12 s, or opened for another address or key, is closed unused. `GNANI_TTS_SPARE=0` turns it off. Measured on the real service: first audio about 300 ms sooner per sentence. Cost: one idle connection open while the process runs (Gnani allowed 8 at once).
- **Loan event.** `LoanSession` now calls a listener with `{"type": "loan", ...the calculator's figures...}` after each new quote, and `app.py` hands it the transport's `send_event`, as it does for orders. The call page has no panel for it yet; that is the UI session's work. The figures are the calculator's, never the model's, and a failing page never breaks the call.
- **Scorer.** T-WER (English words missed, counting the Hindi or Telugu name of the same product as right) and the cut-off measures (turns split into pieces by the endpointing, turns with under half the words heard, agent clips the caller cut short with no interruption scripted) are now in every scored run. A product word is the only English word known in both scripts, so T-WER is a floor on what the recogniser got right, not a full measure.
- **Loan scheme figures could not be verified (2026-11-03).** The figures (Micro Finance up to Rs 1.40 lakh cost, 6.5 percent; Term Loan up to Rs 50 lakh, 8 percent, loan cap Rs 45 lakh; margin 10 percent; moratorium 3 and 6 months) come from SIH 2026 problem statement PS 26091. A search found no public page for that statement or a scheme with the same figures; the nearest real schemes (for example UP CM Yuva, Bank of India Udyami Vanita) differ. So the README may say only: "figures from the problem statement's scheme terms, indicative" and must not present them as a bank's or government's current terms.

### DEC-049 · One neutral palette for every page; glass, glows and the admin's lime removed (2026-11-05)
Surya looked at the dark call page (navy surfaces, green, blue and amber glows behind blurred cards) and asked for the colour theme to change everywhere. Chosen from the options offered: **neutral charcoal, no glows, in both light and dark.**
- **One token file.** Light: bg `#F3F3F1`, cards `#FFFFFF`, ink `#1C1C1E`, green `#1F7A4D`. Dark: bg `#141415`, cards `#1D1D1F`, ink `#ECECEE`, green `#5DBB8A`. `shared/tokens.css` is the only place colours live; all three pages use it.
- **Removed:** `shared/glass.css` (three radial gradients and the backdrop blur), the `--glass`, `--glass-line`, `--blur` and `--blob-*` tokens, and `admin/theme.css` (the near-black and lime override of DEC-042). The admin keeps its dark default, its layout and everything else.
- **The brutalist edge** is near-black in light and near-white in dark. With the old green edge on the dark green button the hard shadow merged into the button and made it look notched.
- **Measured, not judged:** `scripts/ui_check/contrast.py` passes all 44 pairs (22 pairs, 2 themes); the browser audit reports 0 errors and 0 warnings on 24 runs; `snapshots/` was retaken.
- **Supersedes** the glass rule and the blob exception in DEC-041 and the admin palette in DEC-042. **Not tried:** a real phone screen in bright sunlight, or a user's view on whether charcoal feels too plain.

### DEC-050 · A sign-in page and a session cookie instead of the browser's own prompt (2026-11-06)
Surya showed the browser's grey Basic-auth box on the dashboard and asked for a proper login. The box cannot say whose dashboard it is, cannot show a PIN pad, cannot count tries and looks like an error.
- **Why GET and a header.** The server behind the dashboards (the `websockets` library's HTTP hook) answers GET only: no POST, no request body. So the page signs in with one `fetch` GET to `/s/<shop>/dashboard/session` (or `/admin/session`) whose `Authorization: Basic` header carries the PIN, the way a script already did. The PIN is never in a URL. A POST form or a login token in the query string were not possible or were worse (URLs get logged and kept in history).
- **The session.** The reply sets `dd_session`: random 256-bit token, `HttpOnly` (a script on the page cannot read it), `SameSite=Strict` (never sent from another site, so another page cannot sign you out or in), `Secure` when `X-Forwarded-Proto` is https. `auth.SessionStore` keeps tokens in memory with a scope (`admin` or `shop:<name>`): a restart signs everyone out, which is the safe direction. 12 hours, or 30 days if "Keep me signed in on this device" is ticked (`/session/keep`). A new sign-in revokes the browser's old session. Sign out (`/signout`) revokes it and clears the cookie.
- **Scope.** A shop session opens only its own shop, never the admin page; the admin session opens every shop and the admin page.
- **What "not signed in" answers, by who asks** (`login.client_kind`): a browser opening the page gets the sign-in page (401, no `WWW-Authenticate`, so no native box); the page's own background request gets a bare 401 (the page then offers to sign in again; this is why the native box never reappears after a session ends); a script or test with no browser gets 401 and the Basic challenge as before. So every old test and tool still works.
- **Guessing.** Wrong tries are still counted per address and shop (5, then a minute), now also on the sign-in call, which reports `remaining` and `retry_after`; while locked even the right PIN waits. A valid session is not blocked by the lock, which is about guessing.
- **The page** (`web/login.html`, components `shared/login-*`): one card, one field, one primary button. Number pad on a phone with a "Use letters" switch (a PIN may be any text), a show/hide button, a "keep me signed in" box, the error read out in plain words by cause (wrong, empty, locked with a countdown, server unreachable), the form shut and counting down while locked, a shop with no PIN said so, a hidden username field so a password manager can save it, Back to the call page and Admin sign in below. The admin's version starts dark like the admin page. A Sign out button is in both top bars.
- **Not done / not tried:** a real password manager and a real phone keyboard; `https` (the Secure flag is tested, not seen); sessions surviving a restart (they do not, on purpose); the reasons a PIN is forgotten (a person asks the admin to set a new one, as before); two people signed in at once to one shop (works, each has a cookie).

### DEC-051 · Highlights merged from two prototypes: index tabs and the khata ledger (2026-11-08)
Surya found the way the pages highlight things "so much AI generated": tinted pill badges for a status, a tinted rounded background on the open menu item, a tinted boxed banner, and a dot in front of a live state. The difference had to stay, in a form of its own. Three directions were offered (khata ledger, receipt print, index tabs); he liked two, so both were built as prototypes over the real pages ([snapshots/prototypes/](../snapshots/prototypes/)), and he then chose element by element from their pictures. The result mixes the two:
- **From index tabs:** a status is a solid tab standing on a card's top-right edge (inline in tables); the desktop menu's open item is a tab cut through the menu's edge into the page; menu counts and the attention amounts are small solid tabs; a problem notice is a plain card with a red tab label at its top-left (no coloured line along its top); the shop dashboard's live call is a solid green tab with a notch; freshness is a small tab with a word in it, green LIVE or red OFFLINE, then the time in plain text (changed on 2026-11-09 from a thin green edge, which Surya did not want).
- **From the khata ledger:** the demo-data note is a paper slip (punched holes, a dashed tear line, a NOTE label); the phone menu marks the open item with the accountant's double underline and shows counts as figures behind a rule; the admin's filter tabs are ruled off twice; the live call on the admin page and the call page is an outlined green box with no mark in front (the khata pen caret was dropped on 2026-11-09); a call card's problems are plain italic notes, red when the agent could not answer (the rule on their left, part of the khata look, was dropped on 2026-11-09 at Surya's request); the call page keeps khata's squared chips and outlined labels.
- **Changed from both prototypes, at Surya's request:** the khata labels (IDLE, COMING SOON, INDICATIVE) are straight and clean: the page's own font, a 1 px line, no tilt, no ink texture. The index-tab notice lost its top line.
- **Left out:** khata's red margin line down each card and its double rule under totals (the pictures Surya chose as "overall better" had neither); the receipt-print direction.
- **How it is built:** in the real component CSS, not as a layer. New tokens `--on-ink` (text on a solid tab), `--tab-fold`, `--tab-r`, `--paper`, `--paper-ink`. A notice's label is a real element (`.nlabel`), not CSS `content`, so a screen reader reads it. Which page gets which live-call chip is decided by the page's own stylesheet (`dashboard/layout.css`); which menu style applies is decided by width (901 px and up: tabs; below: khata).
- **Measured:** `contrast.py` passes 62 of 62 pairs (9 new pairs a theme for the tabs, the slip and the notes); the narrowest is white on green in light, 5.32:1.

### DEC-052 · Onboarding on the shop dashboard: richer empty states and a four-step skippable tour (2026-11-09)
Surya pasted a small example (an empty screen that says what will appear and how to start, and a coach mark that highlights one button in a first-time tour) and asked for some research and a version in this product. Two web searches were read first (sources in [frontendgnani.md](frontendgnani.md) section A8). They agree on a few things and not on others, and the build follows only what they agree on.
- **Empty states.** Each empty list says what is missing (a short title), what will appear (one sentence) and, where there is somewhere to start, one action: **Try a call yourself**, which opens that shop's call page. The credit book has no action, because nothing on the dashboard starts a credit entry. The admin's lists still show a plain sentence.
- **The tour.** Four steps on the things the shopkeeper uses first: the Call page link, Orders, Calls and the live-call bar. A ring round the target and a tip beside it, labelled "Step 1 of 4". The example's row of dots was not used, because Surya had asked for no dots. It starts by itself once per browser, on a first visit, and never when the page is opened at an order or when the browser has no storage (it would come back every visit). **Take the tour** in the menu replays it.
- **Always a way out.** Skip tour, a click outside the tip, and Escape each end it; ending it by any route counts as seen. Focus moves into the tip when a step opens (so a screen reader reads its title and text), Tab stays within the tip, and focus goes back to the Take the tour button when it ends. Nothing slides or blinks. The tip's colours are tokens (`--scrim`, `--lift`).
- **Not done.** The admin page and the call page have no tour; the tour is in English only (the Hindi and Telugu wording needs a native reader first, B-16); it was tested in a headless browser at 1280, 390 and 300 px, not on a real phone, with a real screen reader or at 200% zoom (the sources warn that spotlight tours break there first).

### DEC-053 · A live view of the call in progress, for the signed-in shopkeeper only, kept in memory (2026-11-09)
Surya looked at the call page while a phone call was being received by the backend and asked why nothing showed there, "it still holds the previous idea of browser calling", and said that opening the UI should show the active calls, the conversation as it happens and the orders. **Why nothing showed:** the call page draws only what arrives over its own browser connection, and a phone call comes in through the phone provider and never touches a page; the telephony transport also deliberately sent page events to nobody ("a phone provider's socket understands only its own messages"). The dashboard knew that a call was on (the live bar) but not what was said.
- **Decision (Surya's, after being offered four options):** show the conversation, the order being built and the loan quote of the call in progress, for phone calls as well as browser calls.
- **Where:** a **Live** view on the signed-in shop dashboard, not on the call page. The call page is public (it is the link customers open), so showing another caller's words there would show them to any visitor. The dashboard needs the shop's PIN, and a shop's session sees only its own shop's call.
- **How (backend):** `live_feed.py` keeps a copy of the events the agent already sends to a caller's page (what the caller said, what the agent said, the order so far, the quote). `WebSocketTransport.send_event` and the telephony transport's override record each event, so a phone call is kept although nothing is sent to the provider (a test checks that its socket still gets nothing). `live_calls()` returns the call's `channel`, `language`, `lines`, `order` and `loan`, and `dashboard._live_for` puts them in the data the dashboard already polls. No new route, and `app.py` is unchanged.
- **What is kept, and for how long:** in memory only, for the length of the call: the last 60 lines (each cut at 600 characters), the latest order and the latest quote. It is cleared when the call ends or another begins. It is never written to a file, logged or put in the saved call record, which still keeps counts only (`call_stats.py`); a test fails if the module ever uses a file, a log or a print.
- **What stays true:** the Calls view's line "Only counts are kept: no words, no recording, no phone numbers" is about saved records and is still true; the Live view says "Shown live to you only. Nothing said here is saved."
- **Rules weighed:** "call recording stays off" and "synthetic data only". A live display that is not stored is not a recording, but it does show what a customer says to the shopkeeper; Surya chose it knowing that. It is easy to remove or narrow: drop `lines` in `_live_for` to keep the order only.
- **Not done:** the public call page still says "Call ended / Press Start call" and does not say that the line is busy when a phone call is on; the live feed is polled every second while a call is on, not pushed; nothing was tried with a real Exotel call in this session (the backend session's real phone calls were used only as saved records).
