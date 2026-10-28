# Tasks

Status: `[ ]` to do · `[/]` in progress · `[x]` done · `[~]` dropped or deferred (say why).
When you tick something, add the date and the build or InBul that carried it.

## Build (Claude and Surya)
### Step 1: Setup
- [/] Move the upstream reference clone outside the project folder ([rules.md](rules.md) R-3). The move failed with permission denied on 2026-10-28; excluded locally meanwhile (DEC-021)
- [x] `git init` (2026-10-28, Build 1000)
- [x] Versioning: `scripts/changelog.mjs`, `MD/builds/`, `CHANGELOG.md` (2026-10-28, InBul01)
- [ ] `.gitignore`: add `orders/`, `eval/audio/`, `.env`
- [ ] Take the client name out of CLAUDE.md, then commit it (DEC-022)
- [ ] `GNANI_API_KEY` and `GEMINI_API_KEY` in `local_config.example.py` and the key-loading block (`ai_caller_final3.py` ~93–120)
- [ ] `gnani-vachana` and `websockets` in `requirements.txt`
- [ ] Default `CALL_DATA_ENABLED` to `0` (DEC-007)
- [ ] Fix B-01 (the placeholder project check)

### Step 2: Smoke test
- [ ] Read the account's concurrent-session and request limits on app.gnani.ai (B-07)
- [ ] Note the credit cost per minute of STT and per sentence of TTS (not published)
- [ ] Prisma v3.0 vs v2.5 on the same clips; `codemix` vs `transcribe`; with and without `x-keyterms`
- [ ] Check `commit` closes an utterance, and how fast the `transcript` arrives after it
- [ ] Timbre: check its automatic number reading in Hindi and Telugu (DEC-024); measure its idle timeout
- [ ] `scripts/gnani_smoke_test.py`: Prisma streaming with latency printed
- [ ] Timbre: Hindi, Telugu and Hinglish WAVs; time to first chunk
- [ ] Pick the Timbre voice; pick `hi-IN`, `hi-en` or `auto` for Hinglish
- [ ] Note the credits used per minute of audio

### Step 2b: Udyami loan guidance (DEC-027; build right after the Gnani integration)
- [ ] `loan_calculator.py`: project cost, loan, scheme selection, instalment (pure functions) **with unit tests** for the scheme boundaries (₹1.40 lakh, ₹50 lakh) and the PS's worked example
- [ ] Decide and document the instalment formula (reducing balance, moratorium handling)
- [ ] Slot filling: margin money, business, place, each confirmed back
- [ ] Call-type detection in the first turn (order vs loan guidance), and switching
- [ ] Prompt rules: speak only what the calculator returns; amounts in words; "indicative"
- [ ] Loan summary files in `orders/`
- [ ] 8–10 of the eval scripts cover loan guidance (clean and noisy), with exact expected numbers
- [ ] Check the scheme figures against the official scheme documents before the README states them

### Step 3: `stt_gnani.py`
- [ ] Session thread with its own asyncio loop; headers (`x-model: prisma-v3.0`, `lang_code: hi-IN,en-IN,te-IN`); 1,024-byte framing (DEC-023)
- [ ] `finish()` sends `commit`, collects segments, times out; returns `detected_language_code`
- [ ] `is_stale` and a concurrency semaphore
- [ ] Register `STT_PROVIDER=gnani`
- [ ] `x-keyterms` (≤ 200, JSON-escaped) generated from `products_pricing.md`

### Step 4: `tts_gnani.py` and `tts_provider.py`
- [ ] Warm, persistent WebSocket; one request at a time; recovers after barge-in
- [ ] `synthesize()` via REST
- [ ] Thin pre-pass (explicit language, spoken units) per DEC-024, **with unit tests**
- [ ] `tts_provider.py` (`TTS_PROVIDER`); switch the import in `ai_caller_final3.py`

### Step 5: Gemini with an API key
- [ ] `genai.Client(api_key=…)` when `GEMINI_API_KEY` is set
- [ ] Make the startup project check conditional (line ~3289)
- [ ] `LLM_MODEL` as an env var; default to `gemini-3.5-flash-lite` or `gemini-3.8-flash` (DEC-025, B-06)
- [ ] Read our key's rate limits in AI Studio; size the eval to fit

### Step 6: Language selection
- [x] Mostly settled by Prisma v3.0 (DEC-023), 2026-10-28, InBul02
- [ ] Greeting language: Hinglish plus one Telugu line (DEC-005)
- [ ] Implement it, keeping the per-call language lock

### Step 7: The shop
- [ ] `config.yaml` (prompt and fallbacks)
- [ ] `always_on.md`
- [ ] `products_pricing.md` (~60 items, Hindi and Telugu names)
- [ ] `ordering_payment.md`, `delivery_shipping.md`, `faq.md`, the stubs

### Step 8: Order summary
- [ ] Decide how the order state is updated (structured output vs extraction at hang-up) → DEC-006
- [ ] Raise or rework `LLM_HISTORY=3` so long orders aren't forgotten (B-02)
- [ ] Write `orders/<call_id>.json` and `.txt`; check against the stock list
- [ ] Optional: a small order viewer page

### Step 8b: Udhaar ledger (DEC-026; the first thing cut if time runs short)
- [ ] Synthetic customer list (~15 names, credit limits, opening balances) in the knowledge files
- [ ] `orders/ledger.json` and `ledger.txt`: add to a balance, read a balance, record a promise-to-pay date
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

## Demo and submission (Surya)
- [ ] Register on gnani.ai/internship (college email); get the key and 5,000 credits
- [ ] LinkedIn and X posts **by Nov 5**: a working-demo video, tagged #GnaniAI #GreatIndianAIInternshipChallenge, live **before** submitting; engagement counts at the cutoff
- [ ] Check whether Surya's college or town counts as Tier 2 or 3 (Small Town, Big Build award)
- [ ] The 60-second demo video
- [ ] The 2–3 minute walkthrough video
- [ ] The submission form **by Nov 9**

## Inherited from upstream (lower priority)
- [ ] The edge-case audit upstream never finished (greeting interruption, Bluetooth reconnect mid-call, empty LLM or TTS response, long replies, a hallucinated transcript re-locking the language)
- [ ] The full edge-case re-check (stop mid-reply, repeat in another language, a fresh call starting in Telugu, rapid hang-up and call-back, several interrupts in one call)
