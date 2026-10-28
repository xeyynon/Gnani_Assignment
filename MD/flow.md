# Runtime flow

This builds on the root [flow.md](../flow.md), which describes the code exactly as it is today. This file adds what changes for Dukaan Dost. Lines marked **[NEW]** or **[CHANGE]** don't exist yet.

## Startup (`main()`, around line 3286 of `ai_caller_final3.py`)
1. **[CHANGE]** Check the LLM credentials. If `GEMINI_API_KEY` is set, skip the `GOOGLE_CLOUD_PROJECT` check. Otherwise require a real project (see [bugs.md](bugs.md) B-01 for a hole in today's check).
2. Create `logs/vad_metrics.csv` if it's missing.
3. Build `ConversationManager`, which loads `companies/$COMPANY_NAME/config.yaml` and `knowledge/core/always_on.md`. For us, `COMPANY_NAME=dukaan_dost`.
4. Warm up, in order: STT (`stt_provider.warmup()`), then TTS (**[CHANGE]** `tts_provider.warmup()`), then the LLM.
   - **[NEW]** Gnani warmup should open, and keep, the Timbre WebSocket so the first sentence doesn't pay for a TLS handshake.
5. Register SIGINT and SIGTERM, then start the threads.

## Threads (six)
| Thread | Job |
|---|---|
| watchdog | Detects call start and end from the Bluetooth nodes (`wpctl status`). Bumps `_call_gen`, plays the greeting, resets history |
| loopback_guard | Cuts the ALSA↔BlueZ loopback that WirePlumber keeps recreating (echo prevention) |
| recorder | Reads 30 ms frames, runs webrtcvad, confirms onset (2 frames), streams to STT, detects the end of speech (650 ms hangover) |
| processor | Filters, picks the language, runs the LLM, streams TTS, queues audio |
| playback | Plays with `pw-play`, mutes the echo tail, listens for barge-in between sentences |
| vad_metrics_writer | Writes VAD metrics to CSV off the hot path |

([CLAUDE.md](../CLAUDE.md) says five threads. The sixth, vad_metrics_writer, was added upstream on 2026-08-17.)

## Per call
```
Bluetooth nodes appear ─▶ _call_gen += 1 ─▶ clear history ─▶ drain queues ─▶ greeting
   [NEW] greeting offers languages (Option A) or starts in hi-IN (Option B)
   [NEW] start an empty order for this call_id
Bluetooth nodes gone (debounced) ─▶ stop playback ─▶ [NEW] write orders/<call_id>.json/.txt
   ─▶ clear history ─▶ drain queues
```

## Per utterance
```
recorder
  30 ms frame (960 bytes at 16 kHz s16)
  ├─ webrtcvad + energy gate ─▶ onset confirmed (2 frames)
  ├─ start_streaming_session(language_code=<locked lang>, is_stale=…)
  │     [NEW] stt_gnani: opens wss://api.vachana.ai/stt/v3/stream with lang_code
  ├─ session.feed(frame)  [NEW] stt_gnani regroups into exact 1,024-byte frames, sent at real-time pace
  ├─ interim text ─▶ speculative knowledge prefetch
  └─ 650 ms of silence ─▶ session.finish()
        [NEW] stt_gnani: sends ~600 ms of silence frames, waits for `transcript`, joins segments
        ─▶ (transcript, language_code) ─▶ audio_q

processor
  ├─ drop if from an old call
  ├─ filters: too short, hallucination, acknowledgement, "stop", "repeat"
  ├─ language: native script ▶ romanized keywords ▶ the call's locked language
  │     [NEW] a language change reconnects Prisma with the new lang_code on the next utterance
  ├─ ConversationManager.handle_turn_streaming
  │     knowledge: always_on.md + best-scoring sections of products_pricing.md etc.
  │     [NEW] prompt includes the current order so far
  │     Gemini streams sentences; the first sentence is flushed early at its first comma
  ├─ validator.validate_reply
  ├─ [NEW] normalise numbers and ₹ amounts into words (Timbre needs this)
  ├─ tts_provider.start_streaming_synthesis ─▶ raw 16 kHz s16 PCM chunks
  └─ [NEW] update the order state from the turn ─▶ reply_q

playback
  ├─ pw-play each chunk; continuation chunks play back to back
  ├─ 1.2 s echo-tail mute, then a 0.5 s barge-in listening window between sentences
  └─ the caller talking ─▶ stop playback, drop the rest of the reply
```

## How the order state gets updated (open design question)
Two options. It's not decided yet, so it's tracked in [tasks.md](tasks.md).
1. **Structured output from Gemini:** each reply also returns a JSON block with the order changes. This is the most reliable, but streaming a JSON block alongside speech needs care.
2. **A second, small Gemini call at hang-up** that extracts the order from the transcript. Simple, but the summary isn't live during the call, and the read-back has to come from the conversation itself.
