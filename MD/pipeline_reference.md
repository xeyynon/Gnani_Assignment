# Pipeline reference (as built)

The pipeline exactly as the code runs it, with the Raspberry Pi and Bluetooth transport. What changes for Dukaan Dost is in [flow.md](flow.md); the transport seam is in [pi_free_plan.md](pi_free_plan.md).

## Entry point

```
dukaan_dost/app.py  →  main()
```

Run as: `python3 -m dukaan_dost` from the project root. `SHOP_NAME` (default
`dukaan_dost`) picks a folder under `shops/`; credentials come from
`local_config.py` or env vars — see `local_config.example.py`.

## Startup sequence (`main()`, line ~3286)

1. Validate `GOOGLE_CLOUD_PROJECT` is actually configured (exits if still the
   placeholder).
2. `_init_vad_metrics_csv()` — create `logs/vad_metrics.csv` if missing.
3. Log VAD/barge-in config.
4. Build `ConversationManager(SHOP_DIR, LLM_MODEL, LLM_TOKENS, LLM_TEMP)`
   → loads `shops/<name>/config.yaml` (system prompt + fallback messages)
     and `shops/<name>/knowledge/core/always_on.md` (always-on context).
5. Warm up clients once, before any call can arrive:
   `_stt_warmup()` → `_tts_warmup()` → `_llm_warmup(LLM_MODEL)`.
6. Register `SIGINT`/`SIGTERM` handler → sets `_shutdown` event.
7. Start six daemon threads (see below) and idle-loop until `_shutdown` is set.
8. On shutdown: stop any in-flight playback, join all threads (3s timeout
   each), then `os._exit(0)` (hard exit — see comment in source for why).

## The six threads

| Thread | Function | Role |
|---|---|---|
| watchdog | `watchdog_thread()` | Polls `wpctl status` every `WATCHDOG_SEC` to detect Bluetooth call connect/disconnect; drives greeting, history reset, queue draining |
| loopback_guard | `loopback_guard_thread()` | Every `LOOPBACK_GUARD_SEC`, cuts the ALSA↔Bluez monitor loopback WirePlumber keeps recreating (echo prevention) |
| recorder | `recorder_thread()` | Captures mic audio via `pw-record`, runs VAD framing + onset/hangover detection, streams frames to STT, pushes finished utterances onto `audio_q` |
| processor | `processor_thread()` | Consumes `audio_q`, filters/validates transcript, resolves language, calls the LLM (via `ConversationManager`), streams TTS, pushes audio chunks onto `reply_q` |
| playback | `playback_thread()` | Consumes `reply_q`, plays audio via `pw-play`, manages echo-tail mute and the barge-in checkpoint window between sentence chunks |
| vad_metrics_writer | `vad_metrics_writer_thread()` | Drains `_vad_metrics_q` and appends rows to `logs/vad_metrics.csv` off the hot path |

Threads communicate only through queues/events — no direct calls between
recorder/processor/playback.

## Per-call lifecycle (watchdog_thread)

```
_find_nodes() (wpctl) → bluez_input/bluez_output node names present?
  → call_now = True
      new node vs. tracked node?  → treat as new call (even mid-debounce)
      first time call detected?   → _clear_history() → _drain_queues() → _play_greeting()
  → call_now = False for CALL_END_DEBOUNCE_POLLS in a row
      → _stop_playback() → _clear_history() → _drain_queues()
```

`_call_gen` is bumped on every boundary; every queued item (audio_q, reply_q)
carries the generation it was produced under, so stale work from a just-ended
call can never be spoken into the next one.

## Per-utterance flow (the core pipeline)

```
recorder_thread
  ├─ read 30ms PCM frame from pw-record
  ├─ _is_speech() / _is_speech_strict() (webrtcvad) + _energy() gate
  ├─ onset confirm (VAD_ONSET_CONFIRM_FRAMES) → open StreamingSession
  │     (dukaan_dost.stt_provider.start_streaming_session — Sarvam or
  │      Google, per STT_PROVIDER)
  ├─ feed frames to session.feed() while triggered
  ├─ interim transcripts → _maybe_prefetch_rag() → knowledge_retriever
  │      .prefetch_relevant_context() on a background thread (speculative RAG)
  ├─ hangover (SILENCE_FRAMES of consecutive silence) → session.finish()
  │      → (transcript, language_code)
  └─ push (gen, pcm, duration, vad_metrics, tentative, transcript,
           language_code, stt_wait_ms) → audio_q

processor_thread
  ├─ audio_q.get()
  ├─ discard if gen != _call_gen (stale call)
  ├─ _filter_transcript() — validity/hallucination/ack/stop/repeat checks
  ├─ language resolution:
  │      _detect_native_script_language() (Devanagari/Telugu Unicode ranges)
  │        → overrides everything, updates sticky lock
  │      _detect_indic_language() (romanized keyword markers) → per-turn hint
  │      _locked_language_code (session-sticky, set on first confirmed turn)
  ├─ special-case handling (no LLM call):
  │      _is_acknowledgment() → nothing spoken
  │      _is_repeat_request() → replay _last_reply_wav
  │      _is_stop_request()   → speak STOP_RESPONSES[lang]
  ├─ normal turn:
  │      ConversationManager.handle_turn_streaming(transcript, history,
  │           context, language_code)
  │        ├─ knowledge_retriever.get_relevant_context_maybe_cached()
  │        │      (reuses speculative prefetch if still valid)
  │        ├─ get_core_context() (always_on.md, cached at construction)
  │        ├─ builds one system prompt (base_prompt + core + knowledge)
  │        └─ llm_gemini.stream() → Gemini via Vertex AI, sentence-chunked
  │      per sentence chunk:
  │        validator.validate_reply() (strips banned patterns, greeting
  │           dedupe, language/format gating)
  │        _tts_and_enqueue() → tts_google.synthesize() /
  │           start_streaming_synthesis() → WAV chunk(s)
  │        push (gen, reply_id, wav_chunk, lang, is_last) → reply_q
  ├─ _record_turn() → history + optional _dump_utterance() for STT regression
  └─ cache _last_reply_wav / _last_reply_lang for "repeat" requests

playback_thread
  ├─ reply_q.get()
  ├─ discard if gen != _call_gen
  ├─ _play() → pw-play subprocess, sets _playing event (mutes recorder's
  │      normal capture, echo guard)
  ├─ ECHO_TAIL_SEC mute after playback returns (Bluetooth SCO tail latency)
  ├─ BARGE_IN_LISTEN_SEC checkpoint: briefly unmute between sentence chunks
  │      to catch caller talking again (_caller_speaking event) or continue
  │      with the next chunk of the same reply_id (TTS_CONTINUATION_WAIT_SEC)
  └─ mid-sentence interrupt: recorder_thread can set _mid_play_interrupt
         directly while a chunk is playing → playback_thread kills it early
```

## Module map (`dukaan_dost/`)

| Module | Responsibility |
|---|---|
| `stt_provider.py` | Picks Sarvam vs Google STT (`STT_PROVIDER` env var), exposes `warmup()` / `start_streaming_session()` |
| `stt_sarvam.py` / `stt_google.py` | Provider-specific streaming STT implementations |
| `tts_google.py` | Google TTS synthesis, streaming synthesis, digit-spelling helper, warmup |
| `llm_gemini.py` | Vertex AI Gemini wrapper — `ask()` (blocking), `stream()` (generator), `warmup()` |
| `conversation_manager.py` | Orchestrates one turn: knowledge retrieval + prompt assembly + Gemini call + validation |
| `knowledge_retriever.py` | Loads `shops/<name>/knowledge/*.md`, keyword-scores `##` sections against the transcript, speculative prefetch cache |
| `validator.py` | Post-LLM reply gating (greeting stripping, banned phrases, language checks) |
| `retry.py` | Shared retry/backoff helper used by the network-calling modules |

## Shop configuration (`shops/<name>/`)

```
shops/<name>/
  config.yaml            # system_prompt + fallback_messages (per language)
  knowledge/
    core/always_on.md    # loaded in full, every turn
    *.md                 # topic files, section-scored per turn (KNOWLEDGE_FILES list
                          # in knowledge_retriever.py)
```

Selected via `SHOP_NAME` env var → `SHOP_DIR = shops/<SHOP_NAME>/`
(`dukaan_dost/app.py`, nothing deployment-specific hardcoded in source).

## Supporting/offline scripts (not part of the live call pipeline)

- `evaluation/run_benchmark.py` / `evaluation/analyze_benchmark.py` — STT accuracy benchmark against `evaluation/benchmark_dataset.json`
- `evaluation/stt_regression_test.py` — replays captured call audio through the real streaming STT code path
- `tests/test_streaming_e2e.py` — exercises `ConversationManager.handle_turn_streaming()` → `validate_reply()` → `tts_google.synthesize()` without a live call
