# Models that failed or were ruled out

Inherited from upstream Smart Caller (July–August 2026). These were tested, not guessed. **Don't retry one without new evidence**, and if you do, add the result here.

| Model | Role | What happened | Verdict |
|---|---|---|---|
| OpenAI Whisper (local) | STT | Earliest phase; too slow on a Pi for live calls | Removed |
| Moonshine (offline) + Groq-hosted Whisper | STT | v1 testing phase; replaced by cloud STT built for Indian languages | Removed |
| Google STT `telephony` preset | STT | English only, so worse than Sarvam once Sarvam landed | Deleted from `stt_google.py` |
| Google `chirp` (v1) | STT | Can't do multi-language recognition in **any** region (the API itself says so) | Ruled out |
| Google `chirp_2` | STT | Multi-language only in `eu`, `global` and `us` (no Asia region). Tested worse than `latest_long` on real audio, including mangling the business's own name | Ruled out |
| Google `latest_long` in `asia-south1` | STT | Not available there; `global` is the only location with `latest_long` plus en, hi and te | Use `global` if Google STT is used |
| Sarvam Bulbul | TTS | Worked, but **~40–70% slower to first audio than Google TTS** across several real calls. Sarvam's SDK opened a new HTTP connection per sentence | Dropped 2026-08-17; never committed |
| `gemini-2.5-flash-lite` in `asia-south1` | LLM | 404 in that region for the project; only in `us-central1`, where the India–US round trip would cost more than flash-lite saves | Stayed on `gemini-2.5-flash` (Vertex). **Check again on the API-key path**, which has no region |

## What this means for Gnani
- **Bulbul is the warning for Timbre.** Hold one warm WebSocket and reuse it. Measure time to first audio against Google TTS on the same sentences before declaring Timbre the default.
- **Chirp is the warning for Prisma.** Test on real phone-quality audio, not only clean TTS output, before trusting a WER number.
