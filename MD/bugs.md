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
The greeting is `"Hello! Welcome to {SHOP_NAME}…"`, and the STT-failure apology is English only. Prisma needs a language before the first word.
**Fix:** part of language selection (DEC-005).

### B-05 · Open (risk) · Validator greeting regex is generic
After de-identification, `validator.py` strips any reply that starts "hello/hi/namaste … welcome to …". Fine for us, but check it doesn't strip a legitimate first-turn greeting from the LLM.

### B-07 · Open (risk) · The Gnani account may allow only one active request
Gnani's error docs show `429 RATE_LIMITED`, *"Only 1 active request is allowed at a time"*, for some accounts. The concurrent streaming-session cap is per organisation and only shown on app.gnani.ai. Our pipeline overlaps sessions in three ways: STT for the next utterance while TTS is still speaking, noise-triggered STT sessions (upstream needed 10 at once with Sarvam), and the TTS connection held open between turns.
**Fix:** read the real limit as soon as the key exists. If it's 1–2: one persistent Prisma session per call (feed audio continuously, `commit` at our end of speech) instead of one per utterance; one TTS socket; and ask on Discord whether contest accounts can get more.


### B-08 · Open (risk) · The call page has not been opened in a real browser
The WebSocket server, the protocol and the page's resampler are tested offline, but the page itself (microphone permission, AudioWorklet, playing clips) has never run in a browser. Safari and older browsers may need changes.
**Fix:** task in [tasks.md](tasks.md): try Chrome and Firefox first.

### B-09 · Open (risk) · Possible gaps between sentence clips in the browser
Each sentence is a separate clip, and the server sends the next one only after the page confirms the last one finished. That round trip may leave an audible gap between sentences.
**Fix:** measure it. If audible, let the page queue the next clip while the last one plays.


### B-10 · Open (risk) · The CI/CD workflows have never run on GitHub
They parse, their jobs are wired correctly and the scripts they call are tested, but a real run can still fail on things only GitHub shows: the container build (no Docker engine was available to try it), Python 3.10 on Ubuntu, the release and image steps.
**Fix:** watch the first run after the first push and fix what is red (task in [tasks.md](tasks.md)).


### B-11 · Open · The dashboard has nothing real to show yet
The agent does not write orders, loan summaries or credit balances yet, so the shopkeeper dashboard only shows the demo data from `python -m dukaan_dost.demo_data <shop>`, marked as made up. The data format is fixed (`store.py`) and tested, so this is the writer's job (task in [tasks.md](tasks.md)).

### B-12 · Open (risk) · Sign-in is Basic auth, safe only on localhost or https
The PIN travels in an HTTP header. On plain http across a network it can be read. The server binds `127.0.0.1` by default; for anything else put TLS in front.

### B-13 · Open (risk) · The Gnani backends have never talked to the real service
`stt_gnani.py` and `tts_gnani.py` follow the protocol on docs.gnani.ai (read 2026-11-02) and pass 50 tests against stand-in servers that follow the same pages, so they show the code matches the docs, not that the service matches the docs. Known doubts: the Prisma v3.0 model page and the WebSocket page name the headers differently (`x-model`/`lang_code` vs `model`/`language_code`; both are sent); the model page does not mention `commit` though the WebSocket page documents it (trailing silence is sent as a fallback); whether `format=transcribe` suits Hindi and Telugu numbers. Closed by running `scripts/gnani_smoke_test.py` with a key. Needs the key from app.gnani.ai/voice.

### B-14 · Open (risk) · Every TTS sentence opens a new WebSocket
Each synthesis connects, sends one request and closes (the docs advise one request at a time, and it keeps two sentences from sharing a socket). The TLS and WebSocket handshake adds to time to first audio on every sentence. Unmeasured: experiment E2 shows the cost. If large, keep a small pool of warm connections.

### B-15 · Open · Order totals are still added up by the model
The shop's prompt tells Gemini to add the line prices carefully, but the rule is that money is computed in code and the model only speaks it (research_papers.md: the model can still get a sum wrong). The code that does it (Step 8: check each item against `stock.json`, add the lines, hand the model the total) is not built. Until it is, a total can be wrong. The evaluation must count wrong totals.

### B-16 · Open · The Hindi and Telugu product names have not been checked by a native speaker
The names in `shops/dukaan_dost/stock.json` were written by the assistant. Some may be unnatural or wrong. Matters most for Telugu (the "Main Character" award). A wrong name makes retrieval miss that item for a caller who uses the correct word.

## Fixed, uncommitted
### B-17 · Fixed (uncommitted) · A price was split from its currency word
The reply splitter cut at every full stop followed by a space, so "Atta ka rate Rs. 260 hai." became "Atta ka rate Rs." and "260 hai.", each spoken as a separate clip with a listening pause between them. `next_sentence()` now skips full stops after abbreviations (Rs, Mr, No, ...) and merges fragments shorter than 8 characters into the next sentence. 12 tests (`tests/test_sentence_split.py`).

### B-18 · Fixed (uncommitted) · An interrupted reply was remembered as fully heard
The history stored the whole generated reply even when the caller cut in after the first sentence, so the model carried on as if the unheard part had been said ("sugar added"). `spoken_history.py` records which sentences' audio clips played to the end; after an interruption the history keeps only those (a sentence cut off part-way counts as not heard), or drops the turn if nothing was heard. Hooked into the processor and playback threads in `app.py` (one call per place a reply is abandoned). 14 tests (`tests/test_spoken_history.py`); the thread wiring itself is checked by a source test because the threads can't run in a unit test.

### B-19 · Fixed (uncommitted) · Hindi and Telugu words were cut into pieces by keyword retrieval
`\w+` does not include the vowel signs of Indian scripts, so "आटा" was read as "आट" and the knowledge search was mostly noise for Hindi and Telugu callers. The retriever now treats the Unicode block U+0900 to U+0DFF as word characters. 14 tests (`tests/test_knowledge_retriever.py`).

## Fixed
### B-01 · Fixed in Build 1001 · The startup check missed the example placeholder
`main()` only caught `"your-project-id-here"`, but `local_config.example.py` ships `"your-project-id-or-number-here"`. Now it checks for `"your-project-id"` (both) and for an empty project, via `_gemini_credentials_ok()` (8 tests), and is skipped entirely when `GEMINI_API_KEY` is set, because the Gemini Developer API needs no Google Cloud project.

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
| `/tmp` log filling RAM on the Pi | Redirect to `/dev/null`; rely on the rotating `dukaan_dost.log` |
