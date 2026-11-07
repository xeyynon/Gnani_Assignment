# Bugs and risks

Every bug gets an id, `B-NN`, and moves through three sections:
- **Open**
- **Fixed, uncommitted / awaiting a build:** fixed in the working tree, or committed but not yet in a numbered build or InBul (none at the moment: everything up to 2026-11-05 is in Build 1013 or InBul21)
- **Fixed:** with the build or InBul that carried the fix, e.g. "Fixed in Build 1003" or "Fixed in InBul04"

Fixes to bugs found upstream, before this repo existed, are listed at the end for reference.

## Open
### B-85 · Open (risk) · Steady broadband noise at 10 dB defeats the end-of-speech detector, and nothing is understood
The noisy run of 2026-11-05 (gpt-oss-120b, 15 of 20 calls before the 30-minute limit, so INCOMPLETE and not quotable as a score) got a reply to **none** of its 47 turns. Checked offline on the noise file at the run's level (RMS 713, mean absolute value 589, against the detector's fixed energy gate of 180): webrtcvad marks 99.9 to 100 percent of the noise frames as speech in all four aggressiveness modes, so the recorder is triggered the moment the call starts, runs to the 12-second limit, and sends 12 seconds of noise with the caller's words somewhere in it; Prisma answered "No speech recognized" every time, and the scripted caller waited out its timeouts. Caveats before reading too much into it: the synthetic noise is hiss plus a low rumble plus a 50 and 100 Hz hum, steady for the whole call; real shop noise differs; and the replay transport bypasses the browser, whose call page asks for `noiseSuppression` and `echoCancellation` (so a real browser call is not this bad, a real phone line has its own suppression). What a fix would need: a speech gate relative to a measured noise floor instead of the fixed 180, or noise suppression in front of the detector. Not built. Next: a milder run (20 dB, then 15 dB) to find where the pipeline breaks; a run that gets no replies uses almost no model tokens, so the failing levels are cheap to measure.

### B-83 · Open (risk) · Prisma returned nothing for a one-word answer (1 of 65 turns)
In call h06 of the run of 2026-11-05 the final turn, "Cash" (1.2 s of audio, 19 speech frames), came back as "No speech recognized", the agent apologised, and the order stayed incomplete. All other short answers were heard, so this is rare, but a lost payment word costs the whole order. Possible handling, not built: ask again in a shorter, more specific way once, or retry the same audio with the language hint of the call. To be counted in the next valid run.

### B-39 · Open (risk) · The phone transport has never touched a real provider
`transport_telephony.py` (DEC-046) was built from the Twilio and Exotel documentation and tested against a stand-in that follows the same messages. Both providers gate streaming behind KYC with no published turnaround, and no account exists, so real behaviour is unknown: the exact timing of `mark` replies, whether a `clear` drops audio in flight, and how 8 kHz phone audio affects Prisma's accuracy (the papers say it costs Hindi accuracy; nothing here measures it). Until a real call happens, nothing about the phone line may appear in the README or the video as a result. Decision point Nov 5: if KYC has not cleared, the demo is the browser call.

### B-34 · Open · The first valid evaluation: 9 of 20 orders exactly right (45%) before the catalogue fix
Clean run, gpt-oss-120b, synthetic Timbre speech, saved as `evaluation/results/orders_clean_baseline_retrieval.*`. Totals matched the stock-list arithmetic 20/20, payment 17/20, median time to first audio 2.35 s (90th percentile 2.86 s), WER 0.41 raw and 0.29 number-normalised. Of 11 wrong orders, 8 were items the model refused with "we do not have it" because keyword retrieval had not handed it that product (B-35 below), 3 were quantity or hearing errors ("एक लीटर" heard as "8 लीटर" in d01; two corrections that were dropped as echoes). The catalogue fix and the echo fix target exactly these; a new valid run is needed to measure them (waits on the model's daily limit, B-33).

**2026-11-05 (not a result):** the first run with every fix (gpt-oss-20b) was INVALID because of B-33, but its logs were still read for causes. Of the 7 wrong orders, 5 were the model repeating earlier changes (B-82, now guarded in code), 1 a speech-recognition error that turned "ek litre" into "8 litre" (B-24 again), and 1 the dropped one-word "Cash" (B-83); the rest followed from the daily limit. A valid run after the fixes is still to be taken.

### B-33 · Open (risk) · Groq's daily token limit allows about one full evaluation run a day per model, in a rolling 24 hours
Each model has 200,000 tokens a day on this account (`gpt-oss-20b`; the others have their own counters). A run of 20 calls (65 turns) cost about the whole day on the long prompt, and from call 12 of the third run every turn got the apology fallback ("Rate limit ... tokens per day"), so that run was thrown away. The order prompt was cut by 42 percent (about 3,200 to 1,900 tokens a turn, DEC-041), which lets one run use about 60 percent of a day. Plan runs accordingly: clean on one model, noisy on another or the next day; do not rerun casually. A rate-limited turn is visible in the agent log (`429`, `tokens per day`); the scorer does not yet flag it.

**2026-11-05:** the limit is a rolling 24 hours, not a reset at midnight ("Used 198960 of 200000, try again in 17m"), so a model's tokens come back only as the run that spent them ages out. The first run with every fix (gpt-oss-20b, 20:59 to 21:27) spent the model's budget in its last minutes: 1 turn was refused for the per-minute limit and the last 4 for the daily one, so the scorer marked it INVALID and its 13 of 20 is not quoted. A valid clean run on a model therefore needs its previous full run to be a day old: plan one full run per model per day, and use `--only` for a partial rerun of a few calls.

### B-30 · Open (guarded) · The model re-applied earlier items on a payment turn
On a smoke call "Cash, my name is Ramesh" came back with ops that doubled the whole order (4 kg sugar, 16 L oil, total 2,816). The instructions now say ops come only from the caller's last message, and an example shows a payment-and-name turn with no ops. Unproven: the evaluation counts it. **Guard added 2026-11-03 (uncommitted):** `OrderSession` ignores a note that, on the turn payment is first chosen, adds every existing line again with the same quantity (the doubling shape); any other ops on a payment turn, such as "one more sugar, cash", are applied. Five tests. Narrow on purpose: a wider rule could drop a real change. Whether the model still produces it is for the next scored run.

**2026-11-05:** it was not rare on gpt-oss-20b: 5 of the 7 wrong orders of the first valid-looking run (see B-82). The code guard now covers every turn, not only the first payment turn; whether it is enough is for the next valid run to show, and it stays open until then.

### B-31 · Open · Time to first audio is above the 2 s target
Measured end to end through the real agent (replay caller, Prisma, Groq, Timbre): 2.4 to 4.0 s from the caller's last word to the first audio on the smoke call. Parts seen in the log: the voice detector waits 0.65 s, Prisma 0.2 to 0.4 s, the model 0.6 to 2.2 s, Timbre 0.9 to 1.1 s to the first chunk, and the code-spoken first sentence waits for the model's whole JSON note (the reply is no longer streamed from the model). Candidates: a shorter prompt, a lower hangover, a warm Timbre connection (B-14), speaking an acknowledgement while the model works.

**Part fixed 2026-11-03 (Build 1013):** opening the Timbre connection took 375 to 420 ms, more than the 200 to 300 ms from request to first audio. A spare connection is now kept open ahead of time (`tts_gnani.py`, DEC-047). Measured against the real service, five spoken sentences each way: first audio 454 to 672 ms without the spare, 203 to 312 ms with it after the first (532 ms) sentence of a run. About 300 ms saved per spoken sentence; the end-to-end median is not re-measured yet (it needs a scored run, B-33). Still open: the model's 0.6 to 2.2 s and the 0.65 s hangover. The hangover can now be tuned against the cut-off measure in the scorer instead of by guess.

**2026-11-05:** time to first audio is now counted from the caller's last word (B-57, about 0.3 s more than the old figures say), and the spare-connection artefact of a paced run is fixed (B-81). No valid end-to-end figure exists yet after either change.

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
### B-93 · Fixed in Build 1016 · Short answers on a call ("cash", "that's all") were thrown away because Prisma tagged them with a language the shop does not serve
The agent drops any transcript tagged with a language outside Hindi, Telugu and English, as likely noise. Prisma's automatic language choice is unreliable on short phrases: on the second phone call "नाही, इत नाही, बस इत नाही" was tagged Marathi and discarded, and the caller was apologised to. Measured on synthetic clips through a simulated phone line (a first look at the 64 shortest clips of the order script, `evaluation/audio/orders`, with scratch scripts; its "no difference in the error rate" was wrong, see the full run below): 8 clips came back empty on the phone-band copy against 3 on the clean one, and those were short words. **The full run** (`evaluation/stt_accuracy.py`, all 65 turns, four ways, saved as `evaluation/results/stt_accuracy_prisma`, no language model involved): on a simulated phone line Prisma left 10 of 65 turns empty against 3 clean, and heard 16 turns exactly right against 25; with the language named it left 3 empty and got 19 right on the phone line, and 31 right (none empty) clean. Re-sending the same audio in automatic mode gave the same empty answer every time (0 of 28). Telling Prisma the language fixed all of them: of the 8 clips that failed, automatic detection got 1 right and a session with the language named got 8 ("बस इतना ही।", "అంతే.", "Cash."). So the agent now hears an empty turn again with the language named (the call's own if known, otherwise Hindi then Telugu), only for a turn of 0.4 to 6 seconds where speech was confirmed, and only with Gnani as the recogniser (`STT_LANGUAGE_RETRY=0` switches it off). It costs a few seconds on those turns. Tests: `tests/test_lifecycle_fixes.py` (four new). **Not measured on a real call yet**, and only on synthetic voices: a real accent may behave differently. The simulated phone line is my own (300 to 3,400 Hz band, 8 kHz, mu-law), not Exotel's actual audio. An unresolved part: "एक" heard as "8" (B-24) happens on clean audio too, so it is the model, not the line.

### B-94 · Fixed in Build 1016 · Prisma was never told the call's language, so Telugu short answers were often heard wrongly
From the second turn of a call that is known to be in Hindi or Telugu, the recogniser is now told that language (`app.py`, `_stt_language_for_call`; `STT_USE_CALL_LANGUAGE=0` turns it off). English calls and the first turn of every call stay on automatic detection: told "English", Prisma would garble a caller who slips into Hindi. Evidence, from the full Prisma-alone run (`evaluation/results/stt_accuracy_prisma.md`, 65 synthetic turns, no model, valid): Telugu calls exactly right on 10 of 16 turns with the language named against 5 of 16 on automatic (clean audio); short turns 19 of 31 against 14 of 31; empty answers 0 against 3. The retry of B-93 alone would not have fixed this: most Telugu failures were wrong text, not empty text. Risks: the evidence is synthetic voices and my own phone-line simulation; a caller who changes language in the middle of a call is decoded in the first language (the existing re-lock only reacts to the script of what was heard). Tests: `tests/test_lifecycle_fixes.py` (one new). Not yet confirmed on a real call.

### B-91 · Fixed in Build 1016 · A turn where the model said nothing got "Sorry, I did not catch that", three times in a row
On the second phone call the caller said "My name is Surya." three times and heard "Sorry, I did not catch that" each time. The model returned no changes and no words (nothing to say at that point of the order), and the order code answered a silent, no-change turn with the apology. It now says what comes next: "What would you like to order?" on an empty order, "Anything else?" once there are items (English, Hindi, Telugu). A note the code cannot read at all still gets the apology. Tests: `tests/test_order_turn.py` (three new or changed).

### B-92 · Fixed in Build 1016 · The demo shop sold atta only as a 5 kg bag, so "2 kg atta" was priced as 10 kg
No real kirana lacks loose atta and the small packs. The stock list had one atta item, a 5 kg bag at Rs 260, and the order code counts the caller's number in the item's unit, so "2 kg atta" became 2 bags (Rs 520). The shop now has loose atta by the kilo (`ATTA-1KG`, Rs 55 a kg), the 5 kg bag (`ATTA-5KG`, Rs 260) and a 10 kg bag (`ATTA-10KG`, Rs 510); "atta" and "aata" mean the loose one, the bags are asked for by size. The benchmark scripts (`orders.json` d01, `credit_loans.json` U03) and three retrieval cases now expect `ATTA-1KG`; the product search still finds every item asked for (top 8: 76 of 76 phrases). **Results saved before this change were scored against the old stock**: `credit_loans_clean_120b` (8 of 8) used the old atta, so it is not comparable with a rerun on the new list. Other staples are sold per kg or in small packets already; the Hindi and Telugu names of the new items still need the native-speaker check (B-16).

### B-87 · Fixed in Build 1016 · A long rate limit on the language model silenced a live call
On the first real phone call (2026-11-07 21:42) the Groq model refused two requests ("asked to wait 19s" and "9s") in one minute and the order step got no answer, so the caller heard apologies. The agent gives up on any wait over 2 seconds (a phone call cannot wait), but each Groq model has its own token counters, so the other gpt-oss model was free. `llm_groq.py` now asks the other gpt-oss model once (20b to 120b and back; `LLM_FALLBACK_MODEL` names another, `off` disables it) when the first one asks for a long wait. The evaluation runner sets it to `off` so a run measures one model. Tests: `tests/test_llm_groq.py` (five new). Not yet seen on a real call.

### B-88 · Fixed in Build 1016 (data side) · The dashboard showed nothing after a call where nothing was ordered
The first phone call saved no order ("nothing was ordered"), so the dashboard was empty and gave no sign that a call had happened. Every call now leaves a one-line record `call_<id>.json` in `orders/<shop>/`: when, how long, phone or browser, language, how many turns, how many times the caller cut the agent off, how many turns heard nothing, how many turns the model failed, and the outcome (ordered, loan, nothing). Counts only: no words, no audio, no phone number. The dashboard's `/data` now carries `calls` and `summary.calls_today` / `calls_total`. **The dashboard page does not draw them yet**: that is `dukaan_dost/web/`, which belongs to the UI session. Tests: `tests/test_call_stats.py`, `tests/test_lifecycle_fixes.py` (three new).

### B-89 · Changed in Build 1016, unmeasured · On a phone, short sounds cut the agent's reply off
On the first phone call the agent stopped its own reply 7 times in under a minute: sounds of 1,700 to 3,200 energy (the caller, or someone in the room) lasted four frames (about 120 ms), which is the browser's setting. On a phone line the carrier already removes echo, so a barge-in now needs 8 frames (about 240 ms) when `AUDIO_TRANSPORT=telephony` (`BARGE_IN_MIN_FRAMES` overrides). The greeting is also shorter ("Hello! Welcome to <shop>. How can I help you today?"), because a 9-second greeting was talked over. Whether these help is **not measured**: it needs a second phone call in a quiet room.

### B-90 · Fixed in Build 1016 · Every log line with Hindi or Telugu failed to print on a Windows console
The console's legacy code page raised a "Logging error" traceback for each such line (the call itself was not affected). The agent now switches its console output to UTF-8 at start.

### B-86 · Fixed in Build 1014 · Every call after the first was deaf (a regression from the B-64 fix, in Build 1013)
The B-64 fix made `_clear_history` move the call generation. The recorder thread also calls `_clear_history("new node ...")` a moment after the watchdog has queued the greeting for the new call, so that late reset moved the generation again: the greeting was discarded as "from an earlier call", the greeting guard (which keeps the recorder deaf until the greeting has played) never cleared, and the caller was never heard for the rest of the call. The first call of a run worked, which is why the short live call before the commit passed; the full run that followed (2026-11-05 22:32, search mode) got no reply on 44 of 47 turns. Only the two boundaries the watchdog handles ("call ended ...", "new call") move the generation now. Found within an hour of the merge to `main` by reading the agent log of that run. Tests: `tests/test_lifecycle_fixes.py` (the exact order of events, and which reasons move the generation). Verified live: three calls in a row through the real agent, 3 of 3 orders exactly right, every turn answered. **Lesson, now in the smoke script:** a live check must run at least two calls, because every call boundary is where this class of bug sits (`evaluation/scripts/smoke.json` has two calls).

### B-84 · Fixed in InBul21 · The laptop went to sleep in the middle of an evaluation run and the run ended half done
The credit and loan run of 2026-11-05 shows a 26-minute hole in the agent's log (21:29:34 to 21:55:21) in the middle of its first call, although every wait in the scripted caller is limited to 30 or 40 seconds: the whole machine was asleep while no Claude turn was active. The runner's wall-clock timeout (1,800 s) then stopped the agent after 4 of 8 calls, so the result (4 loan calls right, no credit calls) is incomplete and is not quoted. `run_calls.py` now asks Windows not to sleep while it runs (`SetThreadExecutionState`, ended with the process; nothing in the system settings is changed). Before this change a long run needed someone at the keyboard. Test: `tests/test_score_calls.py` (harmless off Windows and when the call fails).

### B-82 · Fixed in Build 1013 · The model copied earlier changes into later turns, which doubled orders (the main failure of the first valid run)
On the run of 2026-11-05 (gpt-oss-20b, all fixes in), five of the seven wrong orders had one cause: a later note carried the earlier adds again. "Bas itna hi" (that is all) added the same two packets of Maggi a second time and "UPI" a third; "Aur ek Amul butter bhi" also bumped Maggi and Parle-G; a replayed "one kilo less rice" fired again on "Bas, cash". The instructions already say ops come only from the caller's last message, and B-30's first guard only covered the first payment turn. Now `OrderSession.drop_replayed_ops` decides in code, from the caller's own words: an op for a product the caller just named is kept; any other op that is exactly a change made on an earlier turn is dropped; and a sentence that names no product and gives no quantity cannot add or set anything. The conversation manager works out the named products (`named_skus`) and passes them in. Tests: `tests/test_order_turn.py` (the h02 call replayed turn by turn, a replayed remove, a legitimate repeat of a quantity, a sentence with nothing in it) and `tests/test_order_session.py`. Whether the larger model needed it is not known; the next valid run measures it.

### B-41 · Fixed in Build 1013 · A damaged udhaar ledger was silently replaced with the opening balances
`store.read_ledger` turned any read failure into an empty ledger, and `CreditBook._ensure_ledger` then seeded every customer from `opening_balance` and overwrote the file, so a truncated `ledger.json` wiped every real debt and entry. The credit book now reads the ledger strictly: a missing file is a new ledger, a file that is there but unreadable raises `LedgerUnreadable`, nothing is written, and the shop's credit is left to the shopkeeper (`app.py` already catches that at call start; mid-call the order flow treats credit as unknown). Found by the money bug finder and, independently, by the store finder. Tests: `tests/test_credit.py`.

### B-42 · Fixed in Build 1013 · Windows file locks made writes fail with PermissionError, and orders could be saved as pending for no reason
`os.replace` fails on Windows while another thread has the target open (the dashboard reading the ledger). One reader and one writer thread produced 1,244 failures in 1,500 writes in a tight loop; real polling collides far less often but there was no retry, so a hang-up could mark a credit order pending, and the admin tests failed now and then. `store.replace_file` retries a few times (6 tries, 20 to 120 ms) and is used by the order, ledger, PIN, shop-creation and results writes. Tests: `tests/test_credit.py` (a lock waited out).

### B-43 · Fixed in Build 1013 · Removing part of a line could leave a quantity no add would accept
Removing 0.1 kg from 1 kg of sugar left 0.9 kg and removing half a packet from 3 left 2.5 packets, which the read-back then spoke. The remainder is now checked like any quantity and refused with the usual sentence. A line updated and then removed in one note is reported only as removed (it used to say "Updated: ."). Tests: `tests/test_order_session.py`.

### B-44 · Fixed in Build 1013 · A remove with a zero, negative or unreadable quantity deleted the whole line
`_decimal` returns None for 0, negatives and garbage, which the remove code treated like "no quantity", so `remove` with `qty 0` or `"two"` emptied a 5 kg line. Only an absent quantity now removes the whole line; any other bad quantity is refused. Tests: `tests/test_order_session.py`.

### B-45 · Fixed in Build 1013 · The first B-30 guard swallowed "one more maggi, cash" on a one-line order
With a cart of one line, a correct add of the same item and quantity looks exactly like a replay, so the guard dropped it and the caller believed they had two. The narrow guard now needs two or more lines; the general protection is B-82. Tests: `tests/test_order_session.py`.

### B-46 · Fixed in Build 1013 · Ordinary shop talk started the sticky loan mode
"Do you charge interest on udhaar", "is the shop open for business", "what are the business hours", "मेरा व्यापार है, 20 किलो चावल", "I will invest in 10 kg of rice", "ब्याज कितना लगेगा" and the Telugu word for "postpone" all started loan mode, and loan mode lasts for the rest of the call, so the caller could no longer order. The detector now has two kinds of word: strong ones (loan, EMI, Mudra, Udyami, karz, "start a shop") start it alone unless a refusal sits beside them ("no loan, two kilo sugar"); weak ones (interest, business, subsidy, invest, ब्याज, योजना, వడ్డీ ...) only together with lakh, crore or thousand. Tests: `tests/test_loan_flow.py`. Cost: "byaj kitna hai" on its own is no longer a loan question; the caller says "loan" and carries on.

### B-47 · Fixed in Build 1013 · A new customer named Venkatesh was matched to the customer Venkat
The letter-overlap match scored "venkat" against "venkatesh" at 0.80, so the order was approved onto the wrong person's account, which the rule "a wrong person's debt is worse than a pending one" forbids. A longer name that only begins with a known one (more than one letter longer) now scores zero. "Ramesh Kumar" still does not match "Ramesh" and stays pending for the shopkeeper. Tests: `tests/test_credit.py`.

### B-48 · Fixed in Build 1013 · An empty cart was told "your order is noted"
"Cash" as the first message, or after everything was removed, produced the closing sentence while nothing was saved. The closing now needs at least one line. Tests: `tests/test_order_turn.py`.

### B-49 · Fixed in Build 1013 · A tiny loan amount crashed the turn, and a quote of Rs 9 was possible
An amount of 0.4 (or 1e-9) rounded to 0 and made `loan_calculator.quote` raise an uncaught ValueError; an amount of 1 quoted a loan of Rs 9 with an instalment of Rs 0. Amounts under Rs 1,000 are now "not understood" and the calculator's error is caught. Tests: `tests/test_loan_flow.py`.

### B-50 · Fixed in Build 1013 · A Timbre spare connection that had gone quiet failed the sentence for 20 to 30 seconds
The spare connection of DEC-047 was used while it looked open; if the peer no longer answered, the sentence failed after the 20 s timeout and the audio ended 10 s later because the close handshake was awaited inline (also for a stale spare, and at the end of every stream when the server did not answer the close). Closes now run in the background, and a spare that gives no first message in 1.5 s is dropped and the sentence retried once on a fresh connection. Tests: `tests/test_tts_gnani.py`. Checked against the real service afterwards.

### B-51 · Fixed in Build 1013 · A speech segment with no transcript held the speech recogniser for 8 seconds
If the service sent `speech_start` and never a transcript (a segment too short to keep), `finish()` waited the full 8 s. It now waits 1.5 s (`GNANI_STT_SPEECH_OPEN_GRACE_SEC`) after the commit. The number is a judgement, not a measurement: the real service sends the transcript late and without a `processing` message, so a shorter wait would discard real speech. Tests: `tests/test_stt_gnani.py`.

### B-52 · Fixed in Build 1013 · Any HTTP 400 on a schema request turned the strict schema off for the whole run
A context-length 400 added the model to the "does not support json_schema" set for the life of the process, so every later order turn ran in plain JSON mode (B-23's risk). Only an error that mentions the schema does that now. Tests: `tests/test_llm_groq.py`.

### B-53 · Fixed in Build 1013 · A rate limit with a long retry-after was retried at once
A 429 asking for more than 2 s of waiting was retried immediately, which was refused again and spent another request and more tokens. It now gives up at once with a clear log line. Tests: `tests/test_llm_groq.py`.

### B-54 · Fixed in Build 1013 · An error in the middle of a streamed reply was invisible
A mid-stream error event, or a stream that ended without `[DONE]`, left a truncated reply that was spoken as if complete, with nothing in the log. Both are logged as warnings now. Tests: `tests/test_llm_groq.py`.

### B-55 · Fixed in Build 1013 · An inline comment in .env became part of the key
`GROQ_API_KEY=gsk_abc # my key` was read as `gsk_abc # my key`, and a quoted value kept its quotes when a comment followed. A ` #` after an unquoted value and anything after a closing quote are now ignored; a `#` with no space before it stays. Tests: `tests/test_envfile.py`.

### B-56 · Fixed in InBul21 · A scripted barge-in never barged in when the gap between turns was longer than the reply
The scripted caller slept the minimum gap before waiting for the agent to speak, so the reply was over and the interruption landed in silence, and `interrupted_clips` stayed 0. No current script has a barge-in turn, so no result was affected. Barge-in turns now skip the gap and time themselves from the reply's first sound. Tests: `tests/test_transport_replay.py`.

### B-57 · Fixed in InBul21 · Time to first audio was measured from the end of the audio file, not from the caller's last word
The Timbre clips end with a median 0.30 s of silence (mean 0.38 s, longest 1.44 s over the 67 clips), so every earlier figure, including the 2.35 s of the first baseline, was too small by about that much. The scorer now adds the silence back and shows the old figure beside the new one. Existing result files were not rewritten and keep the old meaning. Tests: `tests/test_score_calls.py`, `tests/test_transport_replay.py`.

### B-58 · Fixed in InBul21 · The "10 dB" noise level was about 7.4 dB by the plain definition
The speech level used only samples above 300 (it dropped 45 percent of all samples), and only for the calls kept by `--only`. It is now the RMS of all the speech clips of the full script, the definition is saved with the result and printed in the scorer's title. Tests: `tests/test_score_calls.py`.

### B-59 · Fixed in InBul21 · Edited script text could play stale cached audio
The audio cache was keyed by call id and turn number only, so changing a sentence in a script kept playing the old recording, and a killed run could leave a half-written file that was then reused. The cache now records a hash of (text, language, voice) next to each clip and writes through a temporary file; clips from before that are kept and given a record. Tests: `tests/test_score_calls.py`.

### B-60 · Fixed in InBul21 · A truncated run was reported as valid
A timeout or an early exit of the agent left fewer calls in the result, and the scorer still printed `valid_run: true` with rates over the calls that finished. The run now records whether it completed, the scorer compares the calls that finished with the script, and the table says INCOMPLETE RUN. Tests: `tests/test_score_calls.py`.

### B-61 · Fixed in InBul21 · The model of a run was recorded as the word "default"
Results said `"model": "default"` whenever `LLM_MODEL` was unset. The runner now reads the model and provider the agent itself logged at start. Tests: `tests/test_score_calls.py`.

### B-62 · Fixed in Build 1013 · On a phone call the caller's words and order were also sent to the phone provider
`TelephonyTransport` did not override `send_event`, so the events meant for the browser page (transcripts, order lines, customer names, loan quotes) were written to the provider's socket as non-protocol frames on every turn. Phone sessions now send nothing; a browser on the same server still gets its events. Tests: `tests/test_transport_telephony.py`.

### B-63 · Fixed in InBul21 · A failed write of the run's result file could abort the remaining calls and still mark the run done
On Windows `os.replace` can fail while the runner reads the file. The write is retried, and a write that keeps failing never marks the run done. Tests: `tests/test_transport_replay.py`.

### B-64 · Fixed in Build 1013 · A turn still running at hang-up leaked into the next call
If the caller hung up while the model was thinking and a new call started before it finished, the old reply was written into the new call's history (so the model was told not to greet) and into the "repeat" memory. The generation now moves on before the history is cleared and the old turn's writes are skipped when the generation changed. Tests: `tests/test_lifecycle_fixes.py`.

### B-65 · Fixed in Build 1013 · When speech synthesis failed completely the caller heard nothing but the history said it was said
A sentence was added to the recorded reply before its audio existed. Only sentences that produced audio are recorded now; a reply with no audio at all stays out of the history and the shop's fallback sentence is played once. Tests: `tests/test_lifecycle_fixes.py`.

### B-66 · Fixed in Build 1013 · At hang-up the customer was charged before the order file was written
`OrderSession.close` settled the credit and then wrote the order; a failed write (disk full) left the customer charged and no order for the shopkeeper. The order is written first and the ledger second; if the ledger write fails the order is rewritten as waiting for the shopkeeper. Tests: `tests/test_credit.py`.

### B-67 · Fixed in Build 1013 · One malformed stock.json stopped every call to that shop and the greeting never played
A stock list of the wrong shape raised AttributeError out of the product-name boost into the watchdog, which then repeated "call detected" on every poll, bumping the call generation each time (14 times in 1.5 s). The boost and the conversation manager catch it, a shop that cannot be built answers with a built-in sentence in the caller's language, and the error is logged once per call. `stock.validate` itself never raises now. Tests: `tests/test_lifecycle_fixes.py`, `tests/test_admin_actions.py`.

### B-68 · Fixed in Build 1013 · A loan turn still in flight after hang-up quoted and showed figures to the next page
`LoanSession.apply` had no closed check (the order session did), so a late turn computed a quote and sent it to whichever page was connected, and nothing saved it. A closed session now does nothing. Tests: `tests/test_loan_flow.py`.

### B-69 · Fixed in Build 1013 · "Add one kilo sugar again" was treated as a request to repeat the last reply
The repeat words (again, dobara, phir se) won over the order flow, so the item was dropped; "repeat my order" replayed the previous sentence instead of reading the order; and "repeat that in Hindi" sent the totals through the free model. While an order is active a sentence with a product or a quantity is an order turn, "repeat my order" is read back by the code, and the synthetic instruction never enters the history. The clip-timeout case is no longer counted as heard, and "repeat" right after the greeting replays the greeting. Tests: `tests/test_lifecycle_fixes.py`.

### B-70 · Fixed in Build 1013 · A prefetched knowledge context could be served to another shop or after a price edit
The speculative retrieval cache had one slot keyed by nothing but the words; the next call at another shop, or at the same shop after the owner changed a price, could be answered with the old shop's or the old price's text. The slot now remembers the shop and the modification times of its files. Tests: `tests/test_knowledge_retriever.py`.

### B-71 · Fixed in Build 1013 · A stock edit without a pack size wrote stock.json and then failed, and every later save failed too
`stock.validate` did not check the pack, nor that prices are finite, nor the types of names and aliases, and raised on a null item; `save_stock` wrote `stock.json` before rendering the product file, so a failure left the two out of step. Validation is complete and never raises, and both files are built before either is written. Tests: `tests/test_admin_actions.py`.

### B-72 · Fixed in InBul21 · A call that saved nothing could take the next call's order in the scorer
The scripted calls follow each other with no gap, and the scorer matched an order to a call by a time window that reached 5 s into the next call. Records are now given out in time order, each to one call. Tests: `tests/test_score_calls.py`.

### B-73 · Fixed in InBul21 · Loan calls inflated the headline rows of the score
Every loan call counted as payment right and recall and precision 1.0. Loan calls are now scored on their own row and left out of the order figures. Tests: `tests/test_score_calls.py`.

### B-74 · Fixed in InBul21 · The English-word error rate counted generic Hindi and Telugu words as right
A Latin word's accepted spellings were the union of every product containing it, so "oil" accepted "का", "तेल" and every other oil. Only words that identify exactly one product now count. Tests: `tests/test_score_calls.py`.

### B-75 · Fixed in InBul21 · Rate-limit detection missed Gemini, missed a missing log, and counted every refusal twice
Refused requests are counted once each; Gemini quota failures count; a run with no agent log cannot be verified and is not valid. Tests: `tests/test_score_calls.py`.

### B-76 · Fixed in Build 1013 · A truncated auth.json lost every other shop's PIN on the next PIN change
`auth._load` read any failure as an empty table and `set_pin` wrote it back. Setting a PIN now refuses to write over a file it cannot read; checking a PIN on such a file fails closed; a file of the wrong shape no longer raises. Tests: `tests/test_admin_actions.py`.

### B-77 · Fixed in Build 1013 · Activity-log entries with certain characters disappeared
`str.splitlines` also splits on U+2028, U+2029 and U+0085, which JSON can leave raw inside a note, so such an entry became two bad lines and was skipped. Tests: `tests/test_admin_actions.py`.

### B-78 · Fixed in Build 1013 · A trailing newline passed the shop-name and call-id checks, and an infinite total broke the dashboards
The patterns ended in `$`, which matches before a final newline; they are matched in full now (the stock SKU too). `store._int` did not catch OverflowError, so a record with `"total": 1e999` made the snapshot, and with it the shop and admin pages, raise. Tests: `tests/test_shops_auth_store.py`, `tests/test_admin_actions.py`.

### B-79 · Fixed in Build 1013 · A WebSocket frame that was not a JSON object ended the call
`123` or `[]` made `data.get` raise in the browser transport's handler. Such frames are ignored. Tests: `tests/test_transport_websocket.py`.

### B-80 · Fixed in Build 1013 · The repository's own hygiene check failed on a committed test file, so GitHub's CI would have been red
`scripts/check_repo.py` flagged the made-up `TOKEN` value (24 characters or more, not starting with "test") in the telephony tests as a key assigned in code. It was not seen earlier because the file was untracked until it was committed; the local CI copy passed on the untracked tree. The test secret now starts with "test", which the check allows. Found when the full suite was run after the commit. Tests: `tests/test_ci_scripts.py`.

### B-81 · Fixed in Build 1013 · The spare Timbre connection was thrown away between sentences of a paced run, adding about a second to every reply
In the first valid run, time from request to first audio inside the agent was 2,036 ms at the median against 945 ms the day before. The spare was discarded when older than 12 s, the scripted calls are 22 s or more apart (to stay under the model's rate limit), so every spare was stale and closing it inline plus opening a new one cost more than having no spare. Measured against the real service on 2026-11-05: an idle Timbre connection still answered after 90 s. The limit is now 60 s, the dead-spare check of B-50 covers a connection the server did drop, and the close is in the background. The runs of 2026-11-05 were taken before this change, so their time to first audio carries the artefact and is not quoted. Tests: `tests/test_tts_gnani.py`.

### B-37 · Fixed in Build 1013 · Timbre read six- and seven-digit numbers wrongly in Hindi and Telugu
Played through Timbre and read back with Prisma: "100000" came back as 10000000 in Hindi and 10000 in Telugu; "4500000" as 45000000. English was right, and numbers up to five digits were right in all three languages. For a loan quote that is a serious error (a crore for a lakh). Amounts from one lakh up are now spoken as "1 लाख", "45 లక్షల", "45 lakh" (`loan_session.spoken_amount`), which all came back correct. Order totals stay far below one lakh, but the same function is available if a shop's totals grow. Not yet applied to order sentences.

### B-38 · Fixed in Build 1013 · A name said with "ji" in Hindi script did not match the customer
`रमेश जी` scored 0.73 against `रमेश`, below the match threshold, because only Latin honorifics were removed. Honorifics are now removed in Devanagari and Telugu as well. Found by a test.
### B-35 · Fixed in Build 1013 · The model said "we do not have onions" for items we stock
The order prompt carried only the few product sections that a keyword search picked. It missed items when the Hindi spelling differed by a dot (प्याज vs प्याज़), a Telugu word was plural or spelled differently (బంగాళాదుంపలు vs బంగాళదుంపలు, సబ్బులు), a crowd of similar items (all the oils) filled the 1,200-character budget, or the speech recogniser mis-heard (छेनी for cheeni). The model then told the caller the shop did not sell it. Order turns now send the whole compact catalogue (every SKU with its English, Hindi and Telugu name and unit, 3,400 characters, no prices) and the search supplies only shop facts. On the exact phrases that failed, all six now give the right order. DEC-042.

### B-36 · Fixed in Build 1013 · A caller repeating an item was dropped as an "echo"
`_is_self_echo` (built for the phone line) discarded "टमाटर 1 किलो कर दीजिए" because 89 percent of its words were in the agent's last confirmation. In an order call callers repeat items the agent just said, so corrections vanished (calls d03, t03, e-calls in the baseline run). The filter is now on only for a transport that needs an echo tail (`SELF_ECHO_FILTER=1/0` overrides). Found by reading the agent log of the baseline run.

### B-26 · Fixed in Build 1013 · Prisma rejected the language list, so every turn without a locked language failed
The agent sent `language_code: hi-IN,en-IN,te-IN` when no language was locked yet. The real service answers "exactly one locale is required" (its docs say a list of up to four is allowed on v3.0), the speech turn failed and the agent only apologised. Earlier tests always locked one language, so none met it. `indic-auto` is accepted and detected Hindi, Telugu, English and Hinglish correctly on five test sentences, so it is now the default (`GNANI_STT_LANGUAGES`). Found by the first full-loop run (2026-11-02). docs.gnani.ai disagrees with the service here: trust the service.

### B-27 · Fixed in Build 1013 · Every call after the first had no order
The watchdog opens a call's order and then resets the history with the reason "new node ...", and that reset also closed (and dropped) the order it had just opened. Only the first call of a run could take an order. Now only a "call ended" reset closes the order, and opening a new order first saves any leftover one. 3 regression tests. Found by the first full evaluation run, which scored 0 of 20 until this was fixed. It would have hit browser calls too.

### B-28 · Fixed in Build 1013 · Two orders in the same second would have overwritten each other
Call ids were timestamps to the second. They now end in milliseconds.

### B-29 · Fixed in InBul21 · The scorer left the Hindi full stop on the last word
`।` (U+0964) lies inside the Indian-script range the scorer keeps, so Hindi sentences ending with it counted as wrong words. Found by a test of the scorer.

### B-32 · Fixed in InBul21 · The scripted caller crashed on the admin page's new transport hook
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

### B-40 · Fixed in Build 1013 · A test of the admin page failed now and then by chance
`test_a_generated_pin_is_returned_once_and_works` checked that the generated 6-digit PIN does not appear anywhere in the stored auth file. A run of six digits can appear by chance inside a hex hash, so it failed rarely. It now compares the PIN with the stored values instead of searching the text. One other admin test (`test_an_item_can_be_added_and_removed`) failed once with a permission error while writing a file and could not be reproduced in 12 reruns; it looks like a Windows file lock and is noted, not fixed.
