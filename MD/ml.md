# Models in the stack

| Role | Model | Provider | Why |
|---|---|---|---|
| Speech to text | **Prisma v3.0** (streaming; DEC-023) | Gnani | Contest requirement; detects the language from a hint list; `codemix` output for Hinglish; product names as `x-keyterms`; `commit` to end an utterance. v2.5 kept as a fallback |
| Text to speech | **Timbre v3.0** | Gnani | Contest requirement; one voice covers all 10 languages, so the caller hears the same "person" when the language changes |
| Reasoning | **Gemini** (`gemini-3.5-flash-lite` or `gemini-3.8-flash`; DEC-025) | Google | Evon (Gnani's LLM) isn't on the API. Gemini already streams in this codebase. 2.5 Flash is only served to users who used it before |
| End-of-speech detection | **webrtcvad** (mode 2; mode 3 for barge-in) | Local | Already tuned on real calls; being re-tuned for the browser transport |
| Fallback STT | Sarvam `saaras:v3`, Google STT v2 `latest_long` (global) | Sarvam, Google | Kept as switchable comparisons for the eval |
| Fallback TTS | Google Cloud TTS (streaming) | Google | Kept for A/B comparison and as a failover |

## Choices still open
| Choice | Options | How we'll decide |
|---|---|---|
| Timbre voice | Any of the 13 v3.0 voices (Avinash, Chetana, Devansh, Harshad, Kalpana, Lakshmi, Prakash, Riyaa, Shivani, Shubham, Tarika, Vasudha, Yashraj) | Smoke test: listen to the same Hindi, Telugu and Hinglish lines in 3–4 voices |
| Timbre language for Hinglish | `hi-IN` or `auto` (`hi-en` is documented for v2.5's Poorvi; check it on v3.0) | Smoke test: which reads mixed English words most naturally. Never `auto` for romanized text (it reads as English) |
| Prisma `x-format` | `codemix` or `transcribe` (v3.0) | Eval: which gives better order accuracy on quantities ("do kilo", "2 kg") |
| Prisma keyterms | With or without `x-keyterms` | Eval; Gnani warns context can lower accuracy on some audio |
| Prisma language hint | `hi-IN,en-IN,te-IN` vs `indic-auto` | Eval on short turns, where hints matter most |
| Gemini model | `gemini-3.5-flash-lite` vs `gemini-3.8-flash` | Time to first sentence vs order accuracy, within the key's rate limits |

## Evaluation plan (build step 9)
- **Data:** 20 synthetic order scripts across te, hi, en and Hinglish. Audio comes from Timbre itself or from our own recordings, each in a clean and a noisy version (shop, traffic or fan noise mixed in at ~10 dB SNR).
- **Metrics:**
  - **STT word error rate**, overall and per language.
  - **Order accuracy:** the share of scripts where the final order (items and quantities) exactly matches the script. Also report per-item precision and recall.
  - **Time to first audio:** from the caller stopping speaking to the first agent audio. Upstream logs this as `[SPAN] total_to_first_audio_ms`.
- **Tools:** extend `evaluation/run_benchmark.py` and `evaluation/analyze_benchmark.py`. `evaluation/benchmark_dataset.json` holds 60 generic questions, not orders, so add an order dataset alongside it.
- **Caveat from upstream:** its earlier benchmark voiced Hindi and Telugu through an English TTS voice and got meaningless language results. **Synthesise each script in its own language.**

**No numbers here until they're measured.**
