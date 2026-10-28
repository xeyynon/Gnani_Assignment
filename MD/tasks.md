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
- [ ] `scripts/gnani_smoke_test.py`: Prisma streaming with latency printed
- [ ] Timbre: Hindi, Telugu and Hinglish WAVs; time to first chunk
- [ ] Pick the Timbre voice; pick `hi-IN`, `hi-en` or `auto` for Hinglish
- [ ] Note the credits used per minute of audio

### Step 3: `stt_gnani.py`
- [ ] Session thread with its own asyncio loop; headers; 1,024-byte framing
- [ ] `finish()` flushes silence, collects segments, times out
- [ ] `is_stale` and a concurrency semaphore
- [ ] Register `STT_PROVIDER=gnani`
- [ ] Bias list generated from `products_pricing.md`

### Step 4: `tts_gnani.py` and `tts_provider.py`
- [ ] Warm, persistent WebSocket; one request at a time; recovers after barge-in
- [ ] `synthesize()` via REST
- [ ] Number and ₹ normaliser for en, hi and te, **with unit tests**
- [ ] `tts_provider.py` (`TTS_PROVIDER`); switch the import in `ai_caller_final3.py`

### Step 5: Gemini with an API key
- [ ] `genai.Client(api_key=…)` when `GEMINI_API_KEY` is set
- [ ] Make the startup project check conditional (line ~3289)
- [ ] Try `gemini-2.5-flash-lite` on this path (no region restriction)

### Step 6: Language selection
- [ ] Decide between A (ask in the greeting) and B (start in `hi-IN`) → [decisions.md](decisions.md) DEC-005
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
- [ ] LinkedIn and X posts **by Nov 5**
- [ ] The 60-second demo video
- [ ] The 2–3 minute walkthrough video
- [ ] The submission form **by Nov 9**

## Inherited from upstream (lower priority)
- [ ] The edge-case audit upstream never finished (greeting interruption, Bluetooth reconnect mid-call, empty LLM or TTS response, long replies, a hallucinated transcript re-locking the language)
- [ ] The full edge-case re-check (stop mid-reply, repeat in another language, a fresh call starting in Telugu, rapid hang-up and call-back, several interrupts in one call)
