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
