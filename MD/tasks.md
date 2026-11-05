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
- [ ] Read the account's concurrent-session and request limits on app.gnani.ai (B-07), or run `gnani_smoke_test.py concurrency`
- [ ] Note the credit cost per minute of STT and per sentence of TTS (not published)
- [x] With and without key terms (2026-11-02): 61 main English names help, 200 with Latin aliases hurt (DEC-038)
- [ ] Prisma v3.0 vs v2.5 on the same clips; `codemix` vs `transcribe`
- [x] `commit` closes an utterance; the transcript arrives about 0.4 s later (2026-11-02, smoke test)
- [x] Timbre reads digits correctly in Hindi, Telugu, Hinglish and English (2026-11-02, DEC-038)
- [ ] Timbre: measure its idle timeout
- [x] `scripts/gnani_smoke_test.py` written and tested against stand-in servers (2026-11-02): `tts`, `roundtrip` (with `--keyterms`), `stt`, `concurrency`. **Not yet run with a key**
- [x] Timbre: Hindi, Telugu and Hinglish WAVs; first chunk 515 to 625 ms (2026-11-02, saved in `evaluation/results/`)
- [ ] Pick the Timbre voice; pick `hi-IN`, `hi-en` or `auto` for Hinglish
- [ ] Note the credits used per minute of audio

### Step 2b: Udyami loan guidance (DEC-027; build right after the Gnani integration)
- [x] `loan_calculator.py`: project cost, loan, scheme selection, instalment (pure functions) **with unit tests** for the scheme boundaries (₹1.40 lakh, ₹50 lakh) and the PS's worked example (2026-10-28, InBul07; 38 tests)
- [x] Decide and document the instalment formula (reducing balance, moratorium handling) (2026-10-28, DEC-028)
- [x] Slot filling: the amount, whether own money or project cost, business, place; the amount is read back in the answer (DEC-044, 2026-11-03)
- [x] Call-type detection by keywords in English, Hindi, Telugu and Hinglish; loan mode is sticky for the call (DEC-044)
- [x] The code speaks every figure; amounts of a lakh or more in lakh words because Timbre misreads long digit runs (B-37); the answer says "approximate"
- [x] Loan summary files `orders/<shop>/loan_<id>.json`, shown by the dashboard
- [x] 75 tests (`tests/test_loan_flow.py`); live check on the real model, 4 cases (2026-11-03)
- [x] Four scripted loan calls with expected quotes in `evaluation/scripts/credit_loans.json`; the scorer checks them
- [ ] Run those scripted calls as a scored run (needs model tokens)
- [x] A loan panel on the call page: shows the `loan` event (DEC-047) with the calculator's figures, indicative, no arithmetic in the page; checked through the real `LoanSession`, transport and page in a real browser with a fake microphone (2026-11-03, branch `call-loan-panel`; needs a build)
- [ ] Scheme figures: no public source found for them (DEC-047); Surya to check them against the SIH problem statement itself, and the README states them only as indicative figures from it

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
- [x] M7: T-WER in the scorer (product words count right in Latin or in Hindi or Telugu; 2026-11-03)
- [x] M9: cut-off measures (split turns, under-half turns, unscripted agent cuts) in the scorer next to time to first audio (2026-11-03)
- [x] M8: plain resampling for 8 kHz phone audio (numpy, `transport_telephony.py`, DEC-046, 2026-11-03); not yet measured on real phone audio

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

### Step 5a: Groq as the language model for now (DEC-038)
- [x] `llm_groq.py`, `llm_provider.py`, `LLM_PROVIDER`, startup check, 22 tests (2026-11-02)
- [x] Tried the real shop conversation on Qwen: digits spoken, totals right, unlisted items declined (informal)
- [ ] Pace the evaluation to Groq's 8,000 tokens a minute (B-20)
- [ ] Switch back to Gemini when a key exists; compare the two on the evaluation set

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

### Step 8: The order flow (DEC-039)
- [x] Decide how the order state is updated: the model returns a JSON note per turn, the code applies it (DEC-006, DEC-039) (2026-11-02)
- [x] `order_session.py`: stock check, quantity rules, rounding, sentences in en/hi/te, order and `.txt` files; 59 tests (2026-11-02)
- [x] `order_turn.py`: instructions, strict JSON schema, tolerant reader, reply assembly; `ask_json` on Groq and Gemini; 42 tests (2026-11-02)
- [x] The agent: a fresh order per call, the order saved at hang-up / shutdown / next call, `order` events to the call page; 9 tests (2026-11-02)
- [x] `LLM_HISTORY=3` is enough for orders: the model is shown the order so far every turn (B-02, DEC-039)
- [x] Tried with the real model on Hinglish, Telugu and English orders (informal runs, not saved; see the hand-over)
- [x] The code speaks on every turn that touches the order; prices from the stock list; the shop's own closing sentence; unsold items named (DEC-039)
- [ ] Reduce the prompt (about 2,000 tokens a turn) so more turns fit in Groq's 8,000 a minute (B-20)
- [ ] Optional: offer an in-stock alternative chosen by code, by category (B-21 is closed by saying nothing)
- [ ] Save a scripted order conversation as a repeatable evaluation run (the runs so far were informal)
- [ ] Hindi and Telugu wording of the code-spoken sentences checked by a native speaker (B-16)
- [ ] Optional: a small order viewer page (the shopkeeper dashboard already shows the orders)

### Step 8b: Udhaar ledger (DEC-026; the first thing cut if time runs short)
- [x] Synthetic customer list: 15 customers with limits and opening balances in `shops/<shop>/customers.json` (DEC-045, 2026-11-03)
- [x] `credit.py` over `orders/<shop>/ledger.json`: find a customer by a spoken name, balance, limit check, atomic update (the dashboard already reads the file)
- [x] The code asks for the name, approves within the limit, refuses over it, leaves unknown names to the shopkeeper, answers balance questions
- [x] The order record carries the customer, status and balances; the ledger is settled when the call ends, re-checking the limit
- [x] 79 tests (`tests/test_credit.py`); four scripted credit calls (approved, over the limit, unknown name, balance enquiry) in `evaluation/scripts/credit_loans.json`
- [ ] Live check of the three credit paths on the real model (only the first step was seen live; the rest waits for model tokens)
- [ ] Run the scripted credit and loan calls as a scored run
- [ ] A native speaker checks the customer names in `customers.json` and the credit sentences (B-16)
- [ ] Promise-to-pay dates (deliberately not built)

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
- [x] The agent writes orders at hang-up, so the dashboard shows real calls (B-11, 2026-11-02). Loan summaries and credit balances are still to come
- [x] Call page redesign: call screen, timer, states, live transcript, order panel (empty until step 8), plain error messages (2026-11-02; Build 1007)
- [x] Dashboard redesign to the same look: side menu, icon tiles with change since yesterday, 7-day sales chart, needs-attention list, "soon" for Quick actions, Stock & prices, Reports (2026-11-02; Build 1007)
- [x] The agent sends `order` messages so the call page's Current order fills in (2026-11-02, Build 1008)
- [x] Pages rebuilt as components (shared atoms, panels and scripts; one organism per panel), composed when served (2026-11-02, DEC-040; Build 1007)
- [ ] Shopkeeper labels in Hindi and Telugu
- [x] `python -m dukaan_dost.preview`: look at the dashboard with made-up data and no keys (2026-10-28, InBul13)
- [ ] Try the dashboard on a real phone
- [x] Admin dashboard, read-only: every shop with a state, totals, and a problem list from file checks (2026-11-02, branch `admin-dashboard`, DEC-042; needs a build)
- [x] Admin dashboard, writes: add a shop (blank or a copy) with its PIN, set a PIN, edit the instructions and the stock list, mark warnings solved, an activity log (2026-11-03, branch `admin-dashboard`, DEC-042)
- [ ] Admin dashboard: failed turns per shop (the agent must first write an error log)

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

### Phone number (DEC-046)
- [x] `TelephonyTransport` for Twilio and Exotel streams, fail-closed token, busy line, marks and barge-in, 31 tests against a stand-in provider (2026-11-03)
- [x] Gnani concurrency: 8 Prisma sessions at once, none refused (2026-11-03)
- [ ] Start KYC with one provider (Surya; decision point Nov 5)
- [ ] A public wss address (a tunnel is enough) and `TELEPHONY_TOKEN` set, when an account exists
- [ ] A real call, then a noisy 8 kHz evaluation run (B-39)
