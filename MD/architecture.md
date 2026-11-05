# Architecture

## Today, and after the Gnani work
```
 Browser tab (call page)
   │ microphone, resampled to 16 kHz mono s16
   ▼ WebSocket /ws                   ┌────────── python -m dukaan_dost ───────────────────────┐
 ──────────────────────────────────▶ │  transport_websocket (own thread: serves the page)     │
                                     │     │ capture                                          │
                                     │     ▼                                                  │
                                     │  recorder_thread ── webrtcvad, onset confirm, hangover │
                                     │     │ streams frames                                   │
                                     │     ▼                                                  │
                                     │  stt_provider ──▶ stt_gnani  (Prisma, WSS)   [NEW]     │
                                     │               └─▶ stt_sarvam / stt_google   (kept)     │
                                     │     │ (transcript, lang)                               │
                                     │     ▼                                                  │
                                     │  processor_thread                                      │
                                     │     ├─ filters: hallucination, ack, stop, repeat       │
                                     │     ├─ language lock                                   │
                                     │     ├─ ConversationManager                             │
                                     │     │    ├─ knowledge_retriever (stock list, policies) │
                                     │     │    └─ llm_gemini (API key or Vertex)             │
                                     │     ├─ validator                                       │
                                     │     └─ tts_provider ─▶ tts_gnani  (Timbre, WSS) [NEW]  │
                                     │                     └▶ tts_google               (kept) │
                                     │     │ PCM chunks                                       │
                                     │     ▼                                                  │
 ◀────────────────────────────────── │  playback_thread ── transport.play, echo tail, barge-in│
   WAV clips, one per sentence       │                                                        │
                                     │  watchdog_thread ── call start/end via the transport   │
                                     │     └─ at hang-up: order_writer ─▶ orders/*  [NEW]     │
                                     └────────────────────────────────────────────────────────┘
```

## Audio transport (DEC-029, DEC-032)
Everything between the browser and the pipeline goes through `dukaan_dost/transport.py`. `AUDIO_TRANSPORT` picks the implementation; today there is one, `websocket` (`transport_websocket.py`): it serves the call page at `/` and the call at `/ws`. The pipeline only knows the interface, so a phone-number transport or an offline replay transport (for the evaluation) can be added without touching it. Details and the protocol are in [transport_plan.md](transport_plan.md).

## Many shops and the dashboards (DEC-034)
The transport also routes by shop: `/s/<shop>/ws` is a call for that shop, and the app loads that shop's prompt, knowledge and greeting for the call (`_active_shop`, `_get_conv_mgr`). `dashboard.py` plugs into the same server as an HTTP handler and serves each shop's owner a PIN-protected page (`/s/<shop>/dashboard`) from the JSON files in `orders/<shop>/` (`store.py`). Sign-in and shop names are in `auth.py` and `shops.py`. The agent will write those files at hang-up; today only `demo_data.py` does.

## One call at a time, and what several callers would take (future work, B-39 context, DEC-046)
**Today the agent process serves one call at a time.** A second caller is closed with "busy" (the call page shows a message; the phone transport closes the socket with code 1013). For a neighbourhood shop that is honest and enough. Gnani is not the limit: 8 Prisma sessions ran at once without a refusal (2026-11-03, higher untested).

**Why not simply allow more.** `app.py` was written for one call. The state that belongs to a call, and so would need to become an object per call, is:

| Group | Module-level state in `app.py` |
|---|---|
| Which call | `_call_gen`, `_call_key`, `_capture_key`, `_playback_key`, `_active_shop` |
| Conversation | `_history`, `_spoken` (what was actually heard), `_locked_language_code`, `_no_speech_apologized`, `_last_reply_wav`, `_last_reply_lang` |
| Order, loan, credit | `_order`, `_loan` (and the credit book they hold) |
| Turn-taking | `_playing`, `_greeting_guard`, `_caller_speaking`, `_mid_play_interrupt`, `_abandoned_reply_id`, `_reply_id_counter` |
| Voice activity | `_vad`, `_vad_barge_in`, caller-pitch tracking, `_vad_turn_counter` |
| Recording and metrics | `_dump_seq`, `_call_data_seq`, the metrics queue |
| Threads | five loops (capture, processor, speaker and others) that all read the state above |

Shared safely between calls already: the model client, each shop's `ConversationManager` (`_conv_mgrs`), the stock list, product search.

**The design when it is needed.** One `Call` object holds every row of that table plus its own queues and threads (or asyncio tasks); `app.py` keeps only the process-wide parts (config, logging, the transport, the shared managers, shutdown). The transports already key everything by call (`find_call`, `open_capture(key)`, `play(key, ...)`), so `live_calls()` and the dashboards need only list more than one. Every queued item already carries the call generation, which becomes the call id. Cost: a rewrite of the main file (about 3,400 lines), new tests for isolation (two calls must never share a history, an order or a language lock), and more model quota than the Groq account has.

**Cheaper options before that:** run several agent processes on different ports behind a small router (each keeps its own state, no pipeline change), or keep one call at a time.

## Components
| Component | File | Status |
|---|---|---|
| Main process, five threads plus the transport's server thread | `dukaan_dost/app.py` | Existing; small edits (TTS import, key loading, startup check, order hook) |
| STT dispatcher | `dukaan_dost/stt_provider.py` | Existing; add `gnani` |
| Gnani STT | `dukaan_dost/stt_gnani.py` | **New** |
| TTS dispatcher | `dukaan_dost/tts_provider.py` | **New** |
| Gnani TTS | `dukaan_dost/tts_gnani.py` | **New** |
| Text pre-pass (explicit language, spoken units; Timbre reads numbers itself) | inside `tts_gnani.py` | **New** (DEC-024) |
| Gemini | `dukaan_dost/llm_gemini.py` | Existing; add the API-key client |
| Conversation | `dukaan_dost/conversation_manager.py` | Existing |
| Knowledge | `dukaan_dost/knowledge_retriever.py` | Existing; fixed file names |
| Reply checks | `dukaan_dost/validator.py` | Existing |
| Shop config | `shops/dukaan_dost/` | **New** |
| Order summary | `dukaan_dost/order_writer.py` (proposed) | **New** |
| Evaluation | `evaluation/run_benchmark.py`, `evaluation/analyze_benchmark.py` and new eval scripts | Existing; extend |

## Design principles we keep
- **Threads talk only through queues and events.** Recorder, processor and playback never call each other.
- **Every queued item carries the call generation** (`_call_gen`). Work from a finished call is dropped, never spoken into the next one.
- **Providers sit behind a dispatcher with a fixed interface.** The main file never imports a backend directly. See [integration_handoff.md](integration_handoff.md).
- **Everything tunable is an env var.** No code edit to retune VAD, barge-in or timeouts.
- **Keys come from `local_config.py`, then env vars.** `local_config.py` is gitignored.

The detailed runtime flow is in [flow.md](flow.md).
