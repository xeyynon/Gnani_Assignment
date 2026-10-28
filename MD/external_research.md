# External research

Vendor facts, each with its source and the date read. **Re-check Gnani's facts against https://docs.gnani.ai before relying on them in code.**

## Gnani (read 2026-10-26, via the brief in CLAUDE.md)
### Account
- Key from https://app.gnani.ai/voice. REST header: `X-API-Key-ID: <key>`. **5,000 credits** on registration.
- Python SDK: `pip install gnani-vachana` (Python 3.10+). It reads `GNANI_API_KEY`. `from gnani.tts import GnaniTTSRealtimeClient`; `GnaniSTTStreamClient(api_key, language_code, sample_rate)`. **The SDK doesn't expose the VAD headers**, so use raw `websockets` for STT.
- Evon (Gnani's LLM) is **not** on the API.

### Prisma v2.5: streaming STT
- `wss://api.vachana.ai/stt/v3/stream`. **Every setting goes in the upgrade headers**; there are no query params.
- `lang_code` is required, with **no auto-detect**: `bn-IN en-IN gu-IN hi-IN kn-IN ml-IN mr-IN pa-IN ta-IN te-IN`.
- `x-sample-rate: 16000`; `x-format: verbatim` (the default) or `transcribe` (spoken numbers become digits).
- VAD: `x-vad-threshold` (0.7), `x-min-silence-ms` (500), `x-min-speech-ms` (100), `x-min-segment-ms` (120), `x-max-speech-s`.
- Word boosting: `x-bias-list` (up to 100 words, letters only) and `x-bias-score`.
- Audio: PCM s16le mono, **exactly 1,024 bytes per frame** (32 ms at 16 kHz), **sent at real-time pace**. Bursts hurt VAD.
- Server messages: `connected`, `processing` (the server's VAD saw the end of speech), `transcript` {`text`, `segment_id`, `segment_index`, `audio_duration_ms`, `latency`}, `error`, `settings_updated`.
- **No documented end-of-audio message.** Sessions are capped at **15 minutes**. Changing language means reconnecting.
- REST: `POST https://api.vachana.ai/stt/v3` (multipart `audio_file`, `language_code`; up to 60 s).
- **Still to find out:** the concurrency or rate limit per account; the cost in credits per audio minute; the exact `x-bias-list` separator.

### Timbre: TTS
- Realtime: `wss://api.vachana.ai/api/v1/tts`, header `X-API-Key-ID`. One JSON request per text (see [ml_model_integration.md](ml_model_integration.md)).
- Languages: `auto`, `hi-IN en-IN ta-IN te-IN kn-IN ml-IN mr-IN pa-IN bn-IN gu-IN`, and `hi-en` (Hinglish).
- `timbre-v3.0`: 13 voices, **each covering all 10 languages**: Avinash, Chetana, Devansh, Harshad, Kalpana, Lakshmi, Prakash, Riyaa, Shivani, Shubham, Tarika, Vasudha, Yashraj.
- `timbre-v2.5`: one language per voice (e.g. Poorvi for Hinglish, Lavanya or Suhana for Telugu, Nalini for Hindi).
- Messages: `start`, then `audio` (`data.audio` base64, `data.chunk_index`, `data.is_final`), then `complete`; or `error`.
- **One request at a time per connection.** Wait for `complete`.
- **Numbers, dates and currency must be written as words.**
- REST: `POST https://api.vachana.ai/api/v1/tts/inference` returns WAV. SSE: `POST https://api.vachana.ai/api/v1/tts/sse`.
- **Still to find out:** whether a request can be cancelled mid-stream; the credit cost per character.

## Inherited from upstream research (July–August 2026)
- **Sarvam** concurrency limit: **20 (Starter) / 100 (Pro or Business), account-wide** (docs.sarvam.ai, rate limits page). A real rejection shows as WebSocket close code **1003**; "Timed out waiting for streaming result" is our own 20 s timeout, not Sarvam's.
- **Google STT:** `chirp` has no multi-language support in any region; `chirp_2` only in eu, global and us; `latest_long` with en, hi and te only in `global`.
- **Gemini:** `gemini-2.5-flash-lite` returned 404 in `asia-south1` on Vertex for the upstream project.
- **Telephony:** Twilio, Exotel and Plivo were compared for multi-line calling; parked (DEC-019).
- **Pi:** `/tmp` is tmpfs (RAM-backed, ~1.9 GB cap on a ~3.7 GB Pi).
