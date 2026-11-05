# Bugs and risks

Every bug gets an id, `B-NN`, and moves through three sections:
- **Open**
- **Fixed, uncommitted:** fixed in the working tree, not yet in a build or InBul
- **Fixed:** with the build or InBul that carried the fix, e.g. "Fixed in Build 1003" or "Fixed in InBul04"

Fixes to bugs found upstream, before this repo existed, are listed at the end for reference.

## Open
### B-39 · Open (risk) · The phone transport has never touched a real provider
`transport_telephony.py` (DEC-046) was built from the Twilio and Exotel documentation and tested against a stand-in that follows the same messages. Both providers gate streaming behind KYC with no published turnaround, and no account exists, so real behaviour is unknown: the exact timing of `mark` replies, whether a `clear` drops audio in flight, and how 8 kHz phone audio affects Prisma's accuracy (the papers say it costs Hindi accuracy; nothing here measures it). Until a real call happens, nothing about the phone line may appear in the README or the video as a result. Decision point Nov 5: if KYC has not cleared, the demo is the browser call.

### B-34 · Open · The first valid evaluation: 9 of 20 orders exactly right (45%) before the catalogue fix
Clean run, gpt-oss-120b, synthetic Timbre speech, saved as `evaluation/results/orders_clean_baseline_retrieval.*`. Totals matched the stock-list arithmetic 20/20, payment 17/20, median time to first audio 2.35 s (90th percentile 2.86 s), WER 0.41 raw and 0.29 number-normalised. Of 11 wrong orders, 8 were items the model refused with "we do not have it" because keyword retrieval had not handed it that product (B-35 below), 3 were quantity or hearing errors ("एक लीटर" heard as "8 लीटर" in d01; two corrections that were dropped as echoes). The catalogue fix and the echo fix target exactly these; a new valid run is needed to measure them (waits on the model's daily limit, B-33).

### B-33 · Open (risk) · Groq's daily token limit allows about one full evaluation run a day per model
Each model has 200,000 tokens a day on this account (`gpt-oss-20b`; the others have their own counters). A run of 20 calls (65 turns) cost about the whole day on the long prompt, and from call 12 of the third run every turn got the apology fallback ("Rate limit ... tokens per day"), so that run was thrown away. The order prompt was cut by 42 percent (about 3,200 to 1,900 tokens a turn, DEC-041), which lets one run use about 60 percent of a day. Plan runs accordingly: clean on one model, noisy on another or the next day; do not rerun casually. A rate-limited turn is visible in the agent log (`429`, `tokens per day`); the scorer does not yet flag it.

### B-30 · Open (guarded) · The model re-applied earlier items on a payment turn
On a smoke call "Cash, my name is Ramesh" came back with ops that doubled the whole order (4 kg sugar, 16 L oil, total 2,816). The instructions now say ops come only from the caller's last message, and an example shows a payment-and-name turn with no ops. Unproven: the evaluation counts it. **Guard added 2026-11-03 (uncommitted):** `OrderSession` ignores a note that, on the turn payment is first chosen, adds every existing line again with the same quantity (the doubling shape); any other ops on a payment turn, such as "one more sugar, cash", are applied. Five tests. Narrow on purpose: a wider rule could drop a real change. Whether the model still produces it is for the next scored run.

### B-31 · Open · Time to first audio is above the 2 s target
Measured end to end through the real agent (replay caller, Prisma, Groq, Timbre): 2.4 to 4.0 s from the caller's last word to the first audio on the smoke call. Parts seen in the log: the voice detector waits 0.65 s, Prisma 0.2 to 0.4 s, the model 0.6 to 2.2 s, Timbre 0.9 to 1.1 s to the first chunk, and the code-spoken first sentence waits for the model's whole JSON note (the reply is no longer streamed from the model). Candidates: a shorter prompt, a lower hangover, a warm Timbre connection (B-14), speaking an acknowledgement while the model works.

**Part fixed 2026-11-03 (uncommitted):** opening the Timbre connection took 375 to 420 ms, more than the 200 to 300 ms from request to first audio. A spare connection is now kept open ahead of time (`tts_gnani.py`, DEC-047). Measured against the real service, five spoken sentences each way: first audio 454 to 672 ms without the spare, 203 to 312 ms with it after the first (532 ms) sentence of a run. About 300 ms saved per spoken sentence; the end-to-end median is not re-measured yet (it needs a scored run, B-33). Still open: the model's 0.6 to 2.2 s and the 0.65 s hangover. The hangover can now be tuned against the cut-off measure in the scorer instead of by guess.

### B-02 · Fixed in Build 1008 · The model forgot items in long orders
Every order turn now shows the model the order so far (items and quantities), so the history length no longer matters for the cart. `LLM_HISTORY` stays at 3.

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


### B-10 · Open (risk) · The CI/CD workflows have never been seen running on GitHub
_Update 2026-11-03: reproduced locally with `scripts/ci_local.py` (all green except the container build, which needs Docker running). CI starts only for `main` and pull requests, so pushes to a side branch run nothing; the `build-*` tags start the release workflow. The repository is private, so results can only be read on GitHub._
They parse, their jobs are wired correctly and the scripts they call are tested, but a real run can still fail on things only GitHub shows: the container build (no Docker engine was available to try it), Python 3.10 on Ubuntu, the release and image steps.
**Fix:** watch the first run after the first push and fix what is red (task in [tasks.md](tasks.md)).


### B-11 · Fixed for orders in Build 1008 · The dashboard had nothing real to show
The agent now writes `orders/<shop>/order_<id>.json` (and a readable `.txt`) when a call ends, in the format `store.py` documents; the dashboard reads them (tested: `test_the_dashboard_can_read_what_the_agent_wrote`). Loan summaries and credit balances are still not written.

### B-12 · Open (risk) · Sign-in is Basic auth, safe only on localhost or https
The PIN travels in an HTTP header. On plain http across a network it can be read. The server binds `127.0.0.1` by default; for anything else put TLS in front.

### B-13 · Partly closed · The Gnani backends and the real service
Run against the real service on 2026-11-02 (`gnani_smoke_test.py`, results in `evaluation/results/`): the headers, 1,024-byte framing, `commit`, the 16 kHz raw audio and the digit reading all work, in Hindi, Telugu, English and Hinglish. Found and fixed: the real service never sends the `processing` message the docs describe (B-22). Still open: behaviour under noise and at 8 kHz, long utterances, the concurrent-session limit (`gnani_smoke_test.py concurrency` has not been run), the credit cost, and whether `format=transcribe` or `codemix` suits Hinglish better.

### B-14 · Open (risk) · Every TTS sentence opens a new WebSocket
Each synthesis connects, sends one request and closes (the docs advise one request at a time, and it keeps two sentences from sharing a socket). Measured 2026-11-02: the first audio arrives about 515 to 625 ms after the request, handshake included. How much of that is the handshake is not separated out. If a warm connection saves 100 ms or more, keep a small pool.

### B-15 · Fixed in Build 1008 · Order totals were added up by the model
The code now does all the arithmetic (`order_session.py`) and writes the amounts into the spoken reply, so what the caller hears is what the dashboard shows. The model is told never to state amounts; if it does, a warning is logged. The model can still pick the wrong item or quantity, so order accuracy is what the evaluation measures.

### B-16 · Open · The Hindi and Telugu product names have not been checked by a native speaker
The names in `shops/dukaan_dost/stock.json` were written by the assistant. Some may be unnatural or wrong. Matters most for Telugu (the "Main Character" award). A wrong name makes retrieval miss that item for a caller who uses the correct word.

### B-20 · Open (risk) · Groq's limits on this account are tight
The account's chat models are `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b` (the Llama models in the docs are not available to it). Limits seen in the response headers: 8,000 tokens a minute (shared by the gpt-oss models) and 1,000 requests a day. An order turn is about 2,000 tokens, so about four turns a minute: fine for one caller, not for running the 20 evaluation scripts back to back or for several callers. The evaluation runner must pace itself (about 20 seconds a turn worked). A retry doubles a turn's tokens. Shrinking the prompt (the persona text and the examples) would help. Fallback: Gemini (`LLM_PROVIDER=gemini`) once a key exists.

### B-23 · Open (risk) · The model sometimes breaks the answer format
On the Qwen preview model about a quarter of order turns came back as plain words or broken fragments ('{done', '{"opts'), even with a strict schema, and some retries hit the rate limit. On `openai/gpt-oss-20b` and `120b` it did not happen in about 25 real calls, so the default is now gpt-oss-20b. The safety net stays: Groq's JSON mode returns the plain text, the conversation manager asks once more, and otherwise the fallback message is spoken, never the plain words. The placeholders are `[LINES]` and `[ORDER]` because `{ORDER}` was once answered as the bare text.

### B-24 · Open (risk) · The model can still misread or drop an item
Seen on real calls: "do kilo chini" read as 1 kilo (Qwen/gpt-oss-20b, before the number-word list was added), and "dragon fruit and two packets of Parle-G" adding nothing (before the one-op-per-item rule). Both were fixed in the instructions and then worked, but a few conversations prove little: the evaluation measures order accuracy (items and quantities) on 20 scripts and decides how big this risk is.

### B-21 · Fixed by design in Build 1008 · The model suggested unrelated alternatives for an out-of-stock item
It offered besan or bhujia for paneer. On a turn that touches the order the model's own words are no longer spoken (DEC-039): the code says only that the item is not available. No alternative is offered at all now; adding code-chosen alternatives by category would be an improvement, not a fix.

### B-22 · Fixed in Build 1005 · Every utterance waited about 9 seconds for the transcript
`stt_gnani.py` waited for the `processing` message before finishing. The real service sends `speech_start` and then the `transcript`, with no `processing` in between, so every utterance ran into the timeout. A transcript now also closes the open speech, an answer to the `commit` ends the wait at once, and `finish()` returns when the answer is ready without waiting for the socket to close. Measured: the wait after the caller stops fell from about 9,000 ms to about 400 ms. Two tests added (the case itself, and the slot being freed after the socket closes).

### B-17 · Fixed in Build 1004 · A price was split from its currency word
The reply splitter cut at every full stop followed by a space, so "Atta ka rate Rs. 260 hai." became "Atta ka rate Rs." and "260 hai.", each spoken as a separate clip with a listening pause between them. `next_sentence()` now skips full stops after abbreviations (Rs, Mr, No, ...) and merges fragments shorter than 8 characters into the next sentence. 12 tests (`tests/test_sentence_split.py`).

### B-18 · Fixed in Build 1004 · An interrupted reply was remembered as fully heard
The history stored the whole generated reply even when the caller cut in after the first sentence, so the model carried on as if the unheard part had been said ("sugar added"). `spoken_history.py` records which sentences' audio clips played to the end; after an interruption the history keeps only those (a sentence cut off part-way counts as not heard), or drops the turn if nothing was heard. Hooked into the processor and playback threads in `app.py` (one call per place a reply is abandoned). 14 tests (`tests/test_spoken_history.py`); the thread wiring itself is checked by a source test because the threads can't run in a unit test.

### B-19 · Fixed in Build 1004 · Hindi and Telugu words were cut into pieces by keyword retrieval
`\w+` does not include the vowel signs of Indian scripts, so "आटा" was read as "आट" and the knowledge search was mostly noise for Hindi and Telugu callers. The retriever now treats the Unicode block U+0900 to U+0DFF as word characters. 14 tests (`tests/test_knowledge_retriever.py`).

## Fixed
### B-37 · Fixed (uncommitted) · Timbre read six- and seven-digit numbers wrongly in Hindi and Telugu
Played through Timbre and read back with Prisma: "100000" came back as 10000000 in Hindi and 10000 in Telugu; "4500000" as 45000000. English was right, and numbers up to five digits were right in all three languages. For a loan quote that is a serious error (a crore for a lakh). Amounts from one lakh up are now spoken as "1 लाख", "45 లక్షల", "45 lakh" (`loan_session.spoken_amount`), which all came back correct. Order totals stay far below one lakh, but the same function is available if a shop's totals grow. Not yet applied to order sentences.

### B-38 · Fixed (uncommitted) · A name said with "ji" in Hindi script did not match the customer
`रमेश जी` scored 0.73 against `रमेश`, below the match threshold, because only Latin honorifics were removed. Honorifics are now removed in Devanagari and Telugu as well. Found by a test.
### B-35 · Fixed (uncommitted) · The model said "we do not have onions" for items we stock
The order prompt carried only the few product sections that a keyword search picked. It missed items when the Hindi spelling differed by a dot (प्याज vs प्याज़), a Telugu word was plural or spelled differently (బంగాళాదుంపలు vs బంగాళదుంపలు, సబ్బులు), a crowd of similar items (all the oils) filled the 1,200-character budget, or the speech recogniser mis-heard (छेनी for cheeni). The model then told the caller the shop did not sell it. Order turns now send the whole compact catalogue (every SKU with its English, Hindi and Telugu name and unit, 3,400 characters, no prices) and the search supplies only shop facts. On the exact phrases that failed, all six now give the right order. DEC-042.

### B-36 · Fixed (uncommitted) · A caller repeating an item was dropped as an "echo"
`_is_self_echo` (built for the phone line) discarded "टमाटर 1 किलो कर दीजिए" because 89 percent of its words were in the agent's last confirmation. In an order call callers repeat items the agent just said, so corrections vanished (calls d03, t03, e-calls in the baseline run). The filter is now on only for a transport that needs an echo tail (`SELF_ECHO_FILTER=1/0` overrides). Found by reading the agent log of the baseline run.

### B-26 · Fixed (uncommitted) · Prisma rejected the language list, so every turn without a locked language failed
The agent sent `language_code: hi-IN,en-IN,te-IN` when no language was locked yet. The real service answers "exactly one locale is required" (its docs say a list of up to four is allowed on v3.0), the speech turn failed and the agent only apologised. Earlier tests always locked one language, so none met it. `indic-auto` is accepted and detected Hindi, Telugu, English and Hinglish correctly on five test sentences, so it is now the default (`GNANI_STT_LANGUAGES`). Found by the first full-loop run (2026-11-02). docs.gnani.ai disagrees with the service here: trust the service.

### B-27 · Fixed (uncommitted) · Every call after the first had no order
The watchdog opens a call's order and then resets the history with the reason "new node ...", and that reset also closed (and dropped) the order it had just opened. Only the first call of a run could take an order. Now only a "call ended" reset closes the order, and opening a new order first saves any leftover one. 3 regression tests. Found by the first full evaluation run, which scored 0 of 20 until this was fixed. It would have hit browser calls too.

### B-28 · Fixed (uncommitted) · Two orders in the same second would have overwritten each other
Call ids were timestamps to the second. They now end in milliseconds.

### B-29 · Fixed (uncommitted) · The scorer left the Hindi full stop on the last word
`।` (U+0964) lies inside the Indian-script range the scorer keeps, so Hindi sentences ending with it counted as wrong words. Found by a test of the scorer.

### B-32 · Fixed (uncommitted) · The scripted caller crashed on the admin page's new transport hook
`app.py` began calling `add_ws_handler()` on the transport, which only the browser transport had. The base class now has a no-op, and a test checks that every transport method `app.py` calls exists on the replay transport.

### B-01 · Fixed in Build 1001 · The startup check missed the example placeholder
`main()` only caught `"your-project-id-here"`, but `local_config.example.py` ships `"your-project-id-or-number-here"`. Now it checks for `"your-project-id"` (both) and for an empty project, via `_gemini_credentials_ok()` (8 tests), and is skipped entirely when `GEMINI_API_KEY` is set, because the Gemini Developer API needs no Google Cloud project.

### B-03 · Fixed in Build 1001 · Call recording was on by default
`CALL_DATA_ENABLED` now defaults to off (opt in with `CALL_DATA_ENABLED=1`), and the startup log says whether recording is on (DEC-007).

### B-06 · Fixed in Build 1001 (not yet run against a live key) · The Gemini model was hardcoded
`LLM_MODEL` is now an env var. The default is `gemini-3.5-flash-lite` on the API-key path and still `gemini-2.5-flash` on Vertex. Because Google documents only `thinking_level` for gemini-3.x, the request now sends a `thinking_level` (`minimal`, or `low` on 3.8 Flash, `LLM_THINKING_LEVEL` to override) instead of `thinking_budget=0` for those models. **Both are untested against a real 3.x model**; the smoke test must cover a streamed reply, and if the API refuses the thinking setting, set `LLM_MODEL=gemini-2.5-flash` or adjust `_thinking_config`.

### B-25 · Fixed in Build 1007 · The call page's "agent speaking" state could stick after an interruption
Clips that a stop skipped never counted themselves down, so the playback counter stayed above zero for the rest of the call. A stop now resets the counter and only clips of the current generation count down. Found while rewriting the page (Build 1005); not seen on a real call.

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

### B-40 · Fixed (uncommitted) · A test of the admin page failed now and then by chance
`test_a_generated_pin_is_returned_once_and_works` checked that the generated 6-digit PIN does not appear anywhere in the stored auth file. A run of six digits can appear by chance inside a hex hash, so it failed rarely. It now compares the PIN with the stored values instead of searching the text. One other admin test (`test_an_item_can_be_added_and_removed`) failed once with a permission error while writing a file and could not be reproduced in 12 reruns; it looks like a Windows file lock and is noted, not fixed.
