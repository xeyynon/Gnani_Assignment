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
