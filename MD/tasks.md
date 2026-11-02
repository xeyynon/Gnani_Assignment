# Tasks

Status: `[ ]` to do · `[/]` in progress · `[x]` done · `[~]` dropped or deferred (say why).
When you tick something, add the date and the build or InBul that carried it.

## Build (Claude and Surya)
### Step 1: Setup
- [x] Rename and restructure everything from the earlier project for Dukaan Dost, push-ready (2026-10-28, InBul10, DEC-030)
- [ ] Choose and add a `LICENSE` before making the GitHub repo public (Surya's choice; no licence means all rights reserved)
- [/] Move the upstream reference clone outside the project folder ([rules.md](rules.md) R-3). The move failed with permission denied on 2026-10-28; excluded locally meanwhile (DEC-021)
- [x] `git init` (2026-10-28, Build 1000)
- [x] Versioning: `scripts/changelog.mjs`, `MD/builds/`, `CHANGELOG.md` (2026-10-28, InBul01)
- [ ] `.gitignore`: add `orders/`, `evaluation/audio/`, `.env`
- [x] Take the client name out of CLAUDE.md, then commit it (DEC-022) (2026-10-28, InBul10)
- [x] `GNANI_API_KEY` and `GEMINI_API_KEY` in `local_config.example.py` and the key-loading block (2026-10-28, Build 1001)
- [x] `gnani-vachana==0.9.0` and `websockets>=13` in `requirements.txt` (2026-10-28, Build 1001)
- [x] Default `CALL_DATA_ENABLED` to `0` (DEC-007) (2026-10-28, Build 1001)
- [x] Fix B-01 (the placeholder project check) (2026-10-28, Build 1001)

### Step 2: Smoke test
- [ ] Read the account's concurrent-session and request limits on app.gnani.ai (B-07)
- [ ] Note the credit cost per minute of STT and per sentence of TTS (not published)
- [ ] Prisma v3.0 vs v2.5 on the same clips; `codemix` vs `transcribe`; with and without `x-keyterms`
- [ ] Check `commit` closes an utterance, and how fast the `transcript` arrives after it
- [ ] Timbre: check its automatic number reading in Hindi and Telugu (DEC-024); measure its idle timeout
- [x] `scripts/gnani_smoke_test.py` written and tested against stand-in servers (2026-11-02): `tts`, `roundtrip` (with `--keyterms`), `stt`, `concurrency`. **Not yet run with a key**
- [ ] Timbre: Hindi, Telugu and Hinglish WAVs; time to first chunk
- [ ] Pick the Timbre voice; pick `hi-IN`, `hi-en` or `auto` for Hinglish
- [ ] Note the credits used per minute of audio

### Step 2b: Udyami loan guidance (DEC-027; build right after the Gnani integration)
- [x] `loan_calculator.py`: project cost, loan, scheme selection, instalment (pure functions) **with unit tests** for the scheme boundaries (₹1.40 lakh, ₹50 lakh) and the PS's worked example (2026-10-28, InBul07; 38 tests)
- [x] Decide and document the instalment formula (reducing balance, moratorium handling) (2026-10-28, DEC-028)
- [ ] Slot filling: margin money, business, place, each confirmed back
- [ ] Call-type detection in the first turn (order vs loan guidance), and switching
- [ ] Prompt rules: speak only what the calculator returns; amounts in words; "indicative"
- [ ] Loan summary files in `orders/`
- [ ] 8–10 of the eval scripts cover loan guidance (clean and noisy), with exact expected numbers
- [ ] Check the scheme figures against the official scheme documents before the README states them

### Step 2c: Software-only transport (DEC-029, DEC-032; see [transport_plan.md](transport_plan.md))
- [x] `Transport` interface (2026-10-28, InBul09)
- [x] Browser call page, WebSocket server, Raspberry Pi code and `deploy/` removed (2026-10-28, Build 1002)
- [ ] Try the call page in a real browser (Chrome and Firefox): microphone, a clip playing, hang up, call again (B-08)
- [ ] Measure and close the gap between sentence clips in the browser (B-09)
- [ ] Re-tune per [transport_plan.md](transport_plan.md), one setting at a time, measured: mic mute while the agent speaks, speak-over barge-in, hangover, VAD thresholds
- [ ] `ReplayTransport`: feed recorded or synthetic caller audio through the whole pipeline with no browser, and capture the reply audio and timings (the backbone of the evaluation)
- [ ] Stretch: a phone-number transport on the same WebSocket interface (8 kHz µ-law handling, the provider's barge-in signal)

### Step 2d: Performance (DEC-031)
- [x] Profile the per-frame audio work on a laptop (2026-10-28, `python -m evaluation.profile_frame_cost`): 0.1% of a frame
- [ ] Run the same profile on the machine that will run the demo
- [ ] Only if a function is a visible share of the frame: vectorise it, then consider an optional Cython version with a Python fallback and a parity test

### Step 2e: Fixes found by the research (research_papers.md methods)
- [x] M1: reply splitter keeps "Rs. 260" in one clip, merges fragments under 8 characters (B-17, `next_sentence()`, 12 tests) (2026-11-02)
- [x] M2: an interrupted reply is remembered as only what was heard (B-18, `spoken_history.py`, 14 tests) (2026-11-02)
- [x] Keyword retrieval kept Hindi and Telugu words whole (B-19, 14 tests) (2026-11-02)
- [x] M5: product names given to Prisma as keyterms when a call starts (2026-11-02)
- [ ] M4: the rule layer. The model extracts item and quantity; code checks `stock.json`, adds the lines, and writes the order (this is Step 8)
- [ ] M7: T-WER (English words correct in either script) in the evaluation scoring
- [ ] M9: count cutoffs and time to first audio together in the evaluation
- [ ] M8: plain resampling for 8 kHz phone audio, when a phone number exists

### Step 3: `stt_gnani.py`
- [x] Session thread with its own asyncio loop; headers sent in **both** spellings (DEC-035); 1,024-byte framing, paced in real time (2026-11-02; tested against a stand-in server only)
- [x] `finish()` sends `commit` plus trailing silence, joins segments, times out; returns `detected_language_code` (2026-11-02)
- [x] `is_stale` and a concurrency semaphore (`GNANI_STT_MAX_CONCURRENT_SESSIONS`, default 4 until E5 measures the real cap)
- [x] Register `STT_PROVIDER=gnani` (2026-11-02)
- [ ] Generate the keyterms from `products_pricing.md` (needs the shop content). `set_keyterms()` exists; non-ASCII names are skipped because HTTP headers are ASCII

### Step 4: `tts_gnani.py` and `tts_provider.py`
- [ ] Warm, persistent WebSocket. **Not done:** each synthesis opens its own connection (DEC-035). Decide after E2 shows what the handshake costs (B-14)
- [x] `synthesize()` (2026-11-02): through the documented realtime WebSocket instead of REST, so it reuses the one tested path
- [x] Thin pre-pass `normalize_text()` with unit tests: `Rs. 260` and `₹45` become `260 rupees` / `45 rupees`, `1,25,000` becomes `125000`. Digits are left to Timbre; spelling them out in Hindi/Telugu waits for E2
- [x] `tts_provider.py` (`TTS_PROVIDER`); `app.py` imports from it; startup refuses a Gnani provider with no `GNANI_API_KEY` (2026-11-02)

### Step 5: Gemini with an API key
- [x] `genai.Client(api_key=…)` when `GEMINI_API_KEY` is set (2026-10-28, Build 1001)
- [x] Make the startup project check conditional (2026-10-28, Build 1001)
- [x] `LLM_MODEL` as an env var; default `gemini-3.5-flash-lite` on the API-key path (DEC-025, B-06) (2026-10-28, Build 1001)
- [ ] Run a streamed reply on a live 3.x model; confirm the `thinking_level` setting is accepted (B-06)
- [ ] Read our key's rate limits in AI Studio; size the eval to fit

### Step 6: Language selection
- [x] Mostly settled by Prisma v3.0 (DEC-023), 2026-10-28, InBul02
- [ ] Greeting language: Hinglish plus one Telugu line (DEC-005)
- [ ] Implement it, keeping the per-call language lock

### Step 7: The shop
- [x] `config.yaml` (prompt and fallbacks in en/hi/te) (2026-11-02)
- [x] `always_on.md` (2026-11-02)
- [x] `stock.json` (61 items, English/Hindi/Telugu names, two out of stock) and `products_pricing.md` generated from it by `scripts/build_shop_knowledge.py` (DEC-036, 2026-11-02)
- [ ] **Surya:** a native speaker checks the Hindi and Telugu names in `stock.json` (B-16)
- [x] `ordering_payment.md`, `delivery_shipping.md`, `faq.md` and short real content for the other five fixed files (2026-11-02)
- [ ] Try a real order against the shop with a live Gemini key; tune `system_prompt` (the totals are still worked out by the model, B-15)

### Step 8: Order summary
- [ ] Decide how the order state is updated (structured output vs extraction at hang-up) → DEC-006
- [ ] Raise or rework `LLM_HISTORY=3` so long orders aren't forgotten (B-02)
- [ ] Write `orders/<shop>/order_<call_id>.json` and `.txt`; check against the stock list
- [ ] Optional: a small order viewer page

### Step 8b: Udhaar ledger (DEC-026; the first thing cut if time runs short)
- [ ] Synthetic customer list (~15 names, credit limits, opening balances) in the knowledge files
- [ ] `orders/<shop>/ledger.json` and `ledger.txt`: add to a balance, read a balance, record a promise-to-pay date
- [ ] Prompt rules: confirm the name, the credit limit, unknown names become "credit pending", a neutral tone
- [ ] The order summary carries payment type, customer and balances
- [ ] 4–5 of the 20 eval scripts cover udhaar (add, balance enquiry, over the limit, unknown name)

### Step 9: Evaluation
- [ ] 20 order scripts
- [ ] Clean and noisy audio (~10 dB SNR)
- [ ] Runner: WER, order accuracy, time to first audio
- [ ] A/B against Sarvam and Google TTS as a baseline (if credits allow)
- [ ] Results table

### Step 10: README
- [ ] Problem, diagram, Gnani usage, results, how to run, synthetic-data note

### Step 12: Dashboards (DEC-034)
- [x] Shop registry, PIN sign-in with lock-out, order/loan/ledger file format, demo data (2026-10-28, Build 1003)
- [x] Many shops, one agent: the call link `/s/<shop>/` picks the shop (2026-10-28, Build 1003)
- [x] Shopkeeper dashboard: orders, credit book, loan enquiries, live; checked in a real browser at desktop and phone widths (2026-10-28, Build 1003)
- [ ] The agent writes orders, loan summaries and credit balances at hang-up, so the dashboard shows real calls (B-11; with build steps 7 and 8)
- [x] Call page redesign: call screen, timer, states, live transcript, order panel (empty until step 8), plain error messages (2026-11-02; needs a build)
- [x] Dashboard redesign to the same look: side menu, icon tiles with change since yesterday, 7-day sales chart, needs-attention list, "soon" for Quick actions, Stock & prices, Reports (2026-11-02; needs a build)
- [ ] The agent sends `order` messages so the call page's Current order fills in (with build step 8)
- [ ] Shopkeeper labels in Hindi and Telugu
- [x] `python -m dukaan_dost.preview`: look at the dashboard with made-up data and no keys (2026-10-28, InBul13)
- [ ] Try the dashboard on a real phone
- [ ] Admin dashboard (next): list shops and their status; add a shop from a template and set its PIN; see errors per shop (failed turns, unreadable files, missing knowledge) and mark them solved; edit a shop's prompt and stock list. Needs writes, so it runs over a WebSocket with JSON commands

### Step 11: CI/CD (DEC-033; see [ci_cd.md](ci_cd.md))
- [x] GitHub Actions: CI (tests, lint, repo hygiene, call page, container build), release on `build-*` tags, Dependabot (2026-10-28, InBul12)
- [x] Scripts the pipeline calls, with tests that show they fail on bad input (124 tests in a clean environment)
- [ ] Add the remote and make the first push, joining the GitHub initial commit with `-s ours` ([ci_cd.md](ci_cd.md), "The first push"), then `git push -u origin main --tags`
- [ ] Watch the first CI run and fix anything red: the container build, Python 3.10, Windows (B-10)
- [ ] On GitHub: set the `BANNED_TERMS` variable, turn on branch protection for `main`, make the first image public if wanted
- [ ] Choose and add a `LICENSE`

## Demo and submission (Surya)
- [ ] Register on gnani.ai/internship (college email); get the key and 5,000 credits
- [ ] LinkedIn and X posts **by Nov 5**: a working-demo video, tagged #GnaniAI #GreatIndianAIInternshipChallenge, live **before** submitting; engagement counts at the cutoff
- [ ] Check whether Surya's college or town counts as Tier 2 or 3 (Small Town, Big Build award)
- [ ] The 60-second demo video
- [ ] The 2–3 minute walkthrough video
- [ ] The submission form **by Nov 9**

## Inherited from upstream (lower priority)
- [ ] The edge-case audit upstream never finished (greeting interruption, reconnect mid-call, empty LLM or TTS response, long replies, a hallucinated transcript re-locking the language)
- [ ] The full edge-case re-check (stop mid-reply, repeat in another language, a fresh call starting in Telugu, rapid hang-up and call-back, several interrupts in one call)
