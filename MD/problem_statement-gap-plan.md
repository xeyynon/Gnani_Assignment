# Gap plan: from where we are to each award

**As of 2026-10-26; updated 2026-10-28 after the docs research.** The codebase already handles live calls, barge-in and three languages. Every gap below is about Gnani integration, the shop domain or evidence.

## Gaps that block everything
| Gap | Plan | Task |
|---|---|---|
| No Gnani key | Register at gnani.ai/internship and app.gnani.ai/voice | Surya |
| No Gnani STT or TTS backend | `stt_gnani.py`, `tts_gnani.py`, `tts_provider.py` | Build steps 3–4 |
| Gemini needs a Google Cloud project | Add the API-key path | Build step 5 |
| No shop | `companies/dukaan_dost/` with ~60 items | Build step 7 |
| No order output | `orders/<call_id>.json` and `.txt` | Build step 8 |
| No git | `git init`, after moving the upstream clone out (see [rules.md](rules.md)) | Build step 1 |

## Gaps per award
| Award | What we have | What's missing | Evidence the judges will see |
|---|---|---|---|
| **Mixed Vibes** | Per-call language lock; native-script detection; romanized keyword hints | Prisma v3.0's `detected_language_code` and `codemix` format (DEC-023). Check whether Timbre v3.0 reads Hinglish naturally with `language: hi-IN` | Hinglish demo call; per-language rows in the eval table |
| **Real Deal** | A working phone agent | The order domain: stock list, item and quantity confirmation, total in words, order summary | The summary file on screen in the demo |
| **Noise Canceller** | VAD tuned on a real noisy Bluetooth line; onset debounce; barge-in echo margin | Noisy eval set (~10 dB SNR mixes); Prisma VAD headers tuned | Clean vs noisy WER and order accuracy, side by side |
| **Solo Ninja** | Solo project | Nothing to build. Say it in the submission | Submission text |
| **Main Character** | Telugu worked in the upstream deployment (with Sarvam) | Telugu on Prisma and Timbre, Telugu product names in the stock list, Telugu fallback messages | A Telugu clip in the walkthrough; Telugu rows in the eval |
| **Demo Day Drop** | — | The 60-second video: real call, Hinglish order, one interruption, total read back, summary on screen | The video |

## Risks to the plan
- **Prisma's VAD vs our VAD.** We endpoint locally with webrtcvad; Prisma also runs server-side VAD. On v3.0, `finish()` sends `commit`, so no silence flush is needed.
- **One active request per account (B-07).** If that's our limit, the pipeline's overlapping sessions break. Check first.
- **Gemini access (B-06).** A new key may not get 2.5 Flash, and free-tier daily caps may be small. See [ml_model_integration.md](ml_model_integration.md).
- **5,000 credits.** The eval (20 scripts × clean and noisy × repeats) plus testing can eat credits. Measure the cost per call in the smoke test and budget before running the full eval.
- **Timbre with Telugu numbers.** Timbre now normalises numbers itself, but Telugu coverage is still being refined (DEC-024). Listen to every price in the demo script before recording.
