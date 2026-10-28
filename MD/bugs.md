# Bugs and risks

Every bug gets an id, `B-NN`, and moves through three sections:
- **Open**
- **Fixed, uncommitted:** fixed in the working tree, not yet in a build or InBul
- **Fixed:** with the build or InBul that carried the fix, e.g. "Fixed in Build 1003" or "Fixed in InBul04"

Fixes to bugs found upstream, before this repo existed, are listed at the end for reference.

## Open
### B-02 · Open (design risk) · The LLM forgets items in long orders
`LLM_HISTORY = 3` (past exchanges kept in the prompt) and `LLM_TOKENS = 100` are hardcoded for a Q&A bot. A 10-item order spans far more than 3 exchanges, so by the read-back Gemini can't see the early items, and 100 tokens may cut off a long read-back.
**Fix:** give the prompt an explicit "order so far" block (DEC-006), make `LLM_HISTORY` an env var, and allow more tokens for the read-back turn.

### B-04 · Open (risk) · Greeting and messages assume English first
The greeting is `"Hello! Welcome to {COMPANY_NAME}…"`, and the STT-failure apology is English only. Prisma needs a language before the first word.
**Fix:** part of language selection (DEC-005).

### B-05 · Open (risk) · Validator greeting regex is generic
After de-identification, `validator.py` strips any reply that starts "hello/hi/namaste … welcome to …". Fine for us, but check it doesn't strip a legitimate first-turn greeting from the LLM.

### B-07 · Open (risk) · The Gnani account may allow only one active request
Gnani's error docs show `429 RATE_LIMITED`, *"Only 1 active request is allowed at a time"*, for some accounts. The concurrent streaming-session cap is per organisation and only shown on app.gnani.ai. Our pipeline overlaps sessions in three ways: STT for the next utterance while TTS is still speaking, noise-triggered STT sessions (upstream needed 10 at once with Sarvam), and the TTS connection held open between turns.
**Fix:** read the real limit as soon as the key exists. If it's 1–2: one persistent Prisma session per call (feed audio continuously, `commit` at our end of speech) instead of one per utterance; one TTS socket; and ask on Discord whether contest accounts can get more.

## Fixed, uncommitted
_None._

## Fixed
### B-01 · Fixed in Build 1001 · The startup check missed the example placeholder
`main()` only caught `"your-project-id-here"`, but `local_config.example.py` ships `"your-project-id-or-number-here"`. Now it checks for `"your-project-id"` (both), and is skipped entirely when `GEMINI_API_KEY` is set, because the Gemini Developer API needs no Google Cloud project.

### B-03 · Fixed in Build 1001 · Call recording was on by default
`CALL_DATA_ENABLED` now defaults to off (opt in with `CALL_DATA_ENABLED=1`), and the startup log says whether recording is on (DEC-007).

### B-06 · Fixed in Build 1001 (not yet run against a live key) · The Gemini model was hardcoded
`LLM_MODEL` is now an env var. The default is `gemini-3.5-flash-lite` on the API-key path and still `gemini-2.5-flash` on Vertex. Because Google documents only `thinking_level` for gemini-3.x, the request now sends a `thinking_level` (`minimal`, or `low` on 3.8 Flash, `LLM_THINKING_LEVEL` to override) instead of `thinking_budget=0` for those models. **Both are untested against a real 3.x model**; the smoke test must cover a streamed reply, and if the API refuses the thinking setting, set `LLM_MODEL=gemini-2.5-flash` or adjust `_thinking_config`.

## Fixed upstream, before this repo (for reference; don't reintroduce)
| What | Fix |
|---|---|
| O(n²) pitch detection ran on the whole utterance; caused ~10 s replies | Capped to a 300 ms window |
| `StreamingSynthesis._run` could hang forever if client construction failed | Whole body wrapped so the end sentinel is always sent. **Do the same in `tts_gnani.py`** |
| Playback kept going after a call ended | `gen != _call_gen` check per chunk |
| STT sessions queued after hang-up never cancelled | `is_stale` callback |
| Too-low STT concurrency (self-imposed) | Set from the vendor's documented limit |
| Discarding sub-4-frame noise blips blocked the recorder | Moved to a background thread |
| Two threads wrote `_locked_language_code` | Routed through `_hist_lock` |
| Playback error handler blamed unrelated errors on barge-in | Only suppresses the `pw-play` broken-pipe shape |
| Unlocked lazy singletons and caches | Locks added |
| Synchronous VAD-metrics CSV writes on the hot path | Moved to a writer thread |
| False barge-in interrupts, STT decode bias, repeat-command bug | Fixed 2026-08-19 |
| `/tmp` log filling RAM on the Pi | Redirect to `/dev/null`; rely on the rotating `ai_caller.log` |
