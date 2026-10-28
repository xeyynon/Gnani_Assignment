# Tried and implemented

Approaches that worked and are in the code. Upstream items are already in this folder; Dukaan Dost items get added as they land, with the date and how each was verified.

## Dukaan Dost
| When | What | Verified how |
|---|---|---|
| 2026-10-26 | Checked that this folder equals the latest upstream code with the client removed | `diff --strip-trailing-cr` against a fresh clone; see [helpfromsmartcaller.md](helpfromsmartcaller.md) |
| 2026-10-26 | The `MD/` knowledge folder | — |
| 2026-10-28 | Git, with builds and InBuls (`scripts/changelog.mjs`); Build 1000 is the baseline | Ran `--pending` twice (hand-written part kept) and `--tag`; InBul01 |
| 2026-10-28 | Gemini through an API key (no Google Cloud project), model-aware thinking config, Gnani and Gemini keys, recording off by default (Build 1001) | 13 offline tests in `tests/test_llm_client.py`; the new startup logic run in isolation against six config cases. **Not yet run against a live Gemini or Gnani key** |

## Inherited from upstream (all verified on real calls)
| What | Where |
|---|---|
| Persistent `pw-record` (no Bluetooth crashes); dynamic device discovery (no hardcoded MAC) | `recorder_thread`, `watchdog_thread` |
| Echo control: mute during playback, a 1.2 s echo-tail mute, cutting the WirePlumber loopback links | `playback_thread`, `loopback_guard_thread` |
| Gap-based barge-in: a 0.5 s listening window between sentences, an adaptive noise floor, a speaker-pitch check (300 ms window) | `playback_thread`, the `BARGE_IN_*` and `PITCH_*` env vars |
| Call-generation isolation: every queued item tagged with `_call_gen` | the whole file |
| Session-sticky language plus native-script re-lock plus the greeting-word exception | `processor_thread` |
| Hallucination filters: energy, VAD, words per second, language probability, the supported-language list | `_filter_transcript`, `stt_sarvam.py` |
| "Repeat" (replay the last reply) and "stop" (with per-language responses) | `processor_thread` |
| Speculative knowledge prefetch from interim transcripts | `knowledge_retriever.prefetch_relevant_context` |
| Gemini streamed sentence by sentence; the first sentence flushed at its first comma | `conversation_manager.py` |
| Streaming TTS: the first 2 chunks played as a fast clip, the rest as one clip | `_tts_and_enqueue` |
| eSpeak fallback (English) when TTS fails | `ai_caller_final3.py` ~1687 |
| Shutdown in under a second (`os._exit(0)` after joining threads) | `main()` |
| VAD metrics CSV on a background writer, rotated at 5 MB | `vad_metrics_writer_thread` |
| A disk-space floor for call recording (500 MB) | `CALL_DATA_MIN_FREE_BYTES` (we're turning recording off anyway) |
| Every tuning knob is an env var | the CONFIG section of `ai_caller_final3.py` |
| `[SPAN]` timing logs per turn (STT wait, filter, LLM time to first sentence, TTS first chunk, total to first audio) | `processor_thread` ~2984. **Use these for the time-to-first-audio metric** |
