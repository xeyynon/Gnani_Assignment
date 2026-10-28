# Architecture

## Today, and after the Gnani work
```
                         ┌──────────────── Raspberry Pi ──────────────────────────────┐
 Caller's phone          │                                                            │
   │ GSM call            │  pw-record (16 kHz mono s16)                               │
   ▼                     │     │                                                      │
 Shop phone ─Bluetooth──▶│  recorder_thread ── webrtcvad, onset confirm, hangover     │
  (HFP/SCO)              │     │ streams frames                                       │
                         │     ▼                                                      │
                         │  stt_provider ──▶ stt_gnani  (Prisma, WSS)   [NEW]         │
                         │                └─▶ stt_sarvam / stt_google   (kept)        │
                         │     │ (transcript, lang)                                   │
                         │     ▼                                                      │
                         │  processor_thread                                          │
                         │     ├─ filters: hallucination, ack, stop, repeat           │
                         │     ├─ language lock                                       │
                         │     ├─ ConversationManager                                 │
                         │     │    ├─ knowledge_retriever (stock list, policies)     │
                         │     │    └─ llm_gemini (API key [NEW] or Vertex)           │
                         │     ├─ validator                                           │
                         │     └─ tts_provider ─▶ tts_gnani  (Timbre, WSS)  [NEW]     │
                         │                     └▶ tts_google               (kept)     │
                         │     │ PCM chunks                                           │
                         │     ▼                                                      │
                         │  playback_thread ── pw-play, echo-tail mute, barge-in      │
                         │                                                            │
                         │  watchdog_thread ── call start/end via wpctl               │
                         │     └─ at hang-up: order_writer ─▶ orders/*.json, *.txt [NEW]
                         └────────────────────────────────────────────────────────────┘
```

## Components
| Component | File | Status |
|---|---|---|
| Main process, six threads | `ai_caller_final3.py` | Existing; small edits (TTS import, key loading, startup check, order hook) |
| STT dispatcher | `companies/core/stt_provider.py` | Existing; add `gnani` |
| Gnani STT | `companies/core/stt_gnani.py` | **New** |
| TTS dispatcher | `companies/core/tts_provider.py` | **New** |
| Gnani TTS | `companies/core/tts_gnani.py` | **New** |
| Number and currency normaliser | inside `tts_gnani.py` (or its own module) | **New** |
| Gemini | `companies/core/llm_gemini.py` | Existing; add the API-key client |
| Conversation | `companies/core/conversation_manager.py` | Existing |
| Knowledge | `companies/core/knowledge_retriever.py` | Existing; fixed file names |
| Reply checks | `companies/core/validator.py` | Existing |
| Shop config | `companies/dukaan_dost/` | **New** |
| Order summary | `companies/core/order_writer.py` (proposed) | **New** |
| Evaluation | `run_benchmark.py`, `analyze_benchmark.py` and new eval scripts | Existing; extend |

## Design principles we keep
- **Threads talk only through queues and events.** Recorder, processor and playback never call each other.
- **Every queued item carries the call generation** (`_call_gen`). Work from a finished call is dropped, never spoken into the next one.
- **Providers sit behind a dispatcher with a fixed interface.** The main file never imports a backend directly. See [integration_handoff.md](integration_handoff.md).
- **Everything tunable is an env var.** No code edit to retune VAD, barge-in or timeouts.
- **Keys come from `local_config.py`, then env vars.** `local_config.py` is gitignored.

The detailed runtime flow is in [flow.md](flow.md).
