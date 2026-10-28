# Models in the stack

| Role | Model | Provider | Why |
|---|---|---|---|
| Speech to text | **Prisma v2.5** (streaming) | Gnani | Contest requirement; built for Indian languages; word boosting for product names; a `transcribe` mode that turns spoken numbers into digits |
| Text to speech | **Timbre v3.0** | Gnani | Contest requirement; one voice covers all 10 languages, so the caller hears the same "person" when the language changes |
| Reasoning | **Gemini 2.5 Flash** (`gemini-2.5-flash`) | Google | Evon (Gnani's LLM) isn't on the API. Gemini already streams in this codebase |
| End-of-speech detection | **webrtcvad** (mode 2; mode 3 for barge-in) | Local | Already tuned on a real Bluetooth line |
| Fallback STT | Sarvam `saaras:v3`, Google STT v2 `latest_long` (global) | Sarvam, Google | Kept as switchable comparisons for the eval |
| Fallback TTS | Google Cloud TTS (streaming) | Google | Kept for A/B comparison and as a failover |

## Choices still open
| Choice | Options | How we'll decide |
|---|---|---|
| Timbre voice | Any of the 13 v3.0 voices (Avinash, Chetana, Devansh, Harshad, Kalpana, Lakshmi, Prakash, Riyaa, Shivani, Shubham, Tarika, Vasudha, Yashraj) | Smoke test: listen to the same Hindi, Telugu and Hinglish lines in 3–4 voices |
| Timbre language for Hinglish | `hi-IN`, `hi-en` or `auto` | Smoke test: which reads mixed English words most naturally |
| Prisma `x-format` | `verbatim` or `transcribe` | Eval: which gives better order accuracy on quantities ("do kilo", "2 kg") |
| Prisma language for Hinglish callers | `hi-IN` vs `en-IN` | Eval on the Hinglish scripts |
| Gemini model | `gemini-2.5-flash` vs `-flash-lite` | Upstream switched between them; measure time to first sentence vs quality |

## Evaluation plan (build step 9)
- **Data:** 20 synthetic order scripts across te, hi, en and Hinglish. Audio comes from Timbre itself or from our own recordings, each in a clean and a noisy version (shop, traffic or fan noise mixed in at ~10 dB SNR).
- **Metrics:**
  - **STT word error rate**, overall and per language.
  - **Order accuracy:** the share of scripts where the final order (items and quantities) exactly matches the script. Also report per-item precision and recall.
  - **Time to first audio:** from the caller stopping speaking to the first agent audio. Upstream logs this as `[SPAN] total_to_first_audio_ms`.
- **Tools:** extend `run_benchmark.py` and `analyze_benchmark.py`. `benchmark_dataset.json` holds 60 generic questions, not orders, so add an order dataset alongside it.
- **Caveat from upstream:** its earlier benchmark voiced Hindi and Telugu through an English TTS voice and got meaningless language results. **Synthesise each script in its own language.**

**No numbers here until they're measured.**
