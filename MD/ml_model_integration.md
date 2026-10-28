# Integrating Prisma and Timbre

How Gnani's models plug into the existing pipeline. The API facts (re-verified 2026-10-28) are in [external_research.md](external_research.md), and the interfaces are in [integration_handoff.md](integration_handoff.md). The model choices are DEC-023 (Prisma v3.0) and DEC-024 (Timbre's own number reading).

## Step 0: smoke test first (`scripts/gnani_smoke_test.py`)
Before touching the pipeline. Record every result with its date in [tried_and_implemented.md](tried_and_implemented.md) or [tried_and_failed.md](tried_and_failed.md).
1. **Account limits:** read the concurrent-session and request limits on app.gnani.ai. Open two Prisma sockets at once and a Timbre socket alongside, and see what's refused (B-07).
2. **Prisma:** stream a 16 kHz WAV in 1,024-byte frames every 32 ms. Print each message with a timestamp. Run the same clips through:
   - v3.0 with `hi-IN,en-IN,te-IN` vs `indic-auto` vs v2.5 with a fixed language
   - `codemix` vs `transcribe`
   - with and without `x-keyterms`
3. **`commit`:** send it right after the speech ends and measure the time to the `transcript`. Compare with sending silence and waiting for the server's VAD.
4. **Timbre:** synthesise the same Hindi, Telugu and Hinglish order lines (with ₹ prices and kg or litre quantities) in 3–4 v3.0 voices. Write WAVs, time the first `audio` chunk, and listen to every number. Measure how long an idle socket stays open.
5. **Credits:** note the dashboard balance before and after each step.

## Prisma STT (`stt_gnani.py`)
**Connection:** `wss://api.vachana.ai/stt/v3/stream`. Every setting goes in the upgrade headers:
```
x-api-key-id:       <GNANI_API_KEY>
x-model:            prisma-v3.0              (STT_GNANI_MODEL; empty means v2.5)
lang_code:          hi-IN,en-IN,te-IN        (hints, not a lock; or the call's locked language first)
x-sample-rate:      16000
x-format:           codemix                  (to compare with transcribe in the eval)
x-keyterms:         ["Aashirvaad","toor dal",...]   (≤ 200, JSON with \u escapes for non-ASCII)
x-vad-threshold:    0.7                      (telephony range 0.65–0.75)
x-min-speech-ms:    200                      (noisy line)
x-min-silence-ms:   500
x-idle-timeout-sec: 120                      (callers go quiet while checking what they need)
```
Python `websockets` ≥ 13 takes `additional_headers=`; older versions take `extra_headers=`.

**Threading:** each `StreamingSession` owns a thread running its own asyncio loop, the same shape as `stt_sarvam.py`. `feed()` is called from `recorder_thread` and must never block it.

**Framing:** the recorder hands over 30 ms frames (960 bytes). Keep a buffer and send exact 1,024-byte frames as they fill. They arrive in real time from the mic, so there's no burst-sending.

**Ending an utterance (v3.0):** our recorder decides the caller stopped (650 ms hangover), so `finish()`:
1. sends any partial frame padded with silence to 1,024 bytes
2. sends `{"type": "commit"}`
3. waits, with a timeout, for the `transcript` of that utterance
4. joins every segment's `text` from the session, in `segment_index` order
5. returns `(text, detected_language_code)`, falling back to the requested language if there's no tag.

On v2.5 there's no `commit`: send ~600 ms of silence frames instead and wait for the server's VAD.

**Language:** take `detected_language_code` from each transcript and pass it to the processor's existing lock logic. It's derived from the transcript's script, so it lines up with the native-script detection the processor already trusts (DEC-014). Mostly-English Hinglish can come back tagged `en-IN` (fewer than 30% native letters), so the lock shouldn't flip on one such turn.

**Per-utterance or per-call session:** upstream opens one STT session per utterance. If the account allows only one or two concurrent sessions (B-07), switch to **one session per call**: feed audio continuously, `commit` at each end of speech, and route each `transcript` to the waiting `finish()`. Mind the 15-minute session cap and the idle timeout.

**Keyterms:** generated at startup from `shops/dukaan_dost/knowledge/products_pricing.md`: brand names, plus English, romanized and native-script item names. At most 200, and not every pack-size variant. Gnani warns context can lower accuracy on some audio, so it stays switchable (`STT_GNANI_KEYTERMS=0`) for the eval.

## Timbre TTS (`tts_gnani.py`)
**Streaming:** `wss://api.vachana.ai/api/v1/tts`, header `X-API-Key-ID`. Send one JSON request per sentence:
```json
{"text": "...", "voice": "<chosen v3.0 voice>", "model": "timbre-v3.0",
 "language": "hi-IN", "speed": 1.0,
 "audio_config": {"sample_rate": 16000, "num_channels": 1, "sample_width": 2,
                  "encoding": "linear_pcm", "container": "raw"}}
```
**Set `sample_rate` and `container` explicitly**: the defaults are 48 kHz WAV. Receive `start`, then `audio` messages (`data.audio` is base64 raw PCM), then `complete`. Decode and yield the bytes from `chunks()`.

**Keep the connection warm:** open it in `warmup()` and reuse it. Upstream dropped Sarvam's TTS because opening a fresh connection per sentence made it 40–70% slower to first audio than Google (see [failmlmodel.md](failmlmodel.md)). Idle sockets do time out, so reconnect quietly if the socket was closed between calls.

**One request at a time:** guard the connection with a lock. If barge-in abandons a request, either drain to `complete` in the background or close and reconnect. Measure which is faster.

**`synthesize()`** (greeting, cached replies): `POST https://api.vachana.ai/api/v1/tts/inference` with the same `audio_config` but `container: wav`, which returns 16 kHz LINEAR16 WAV.

**Numbers (DEC-024):** Timbre normalises numbers, ₹ and units itself. Our pre-pass only:
- passes `language` explicitly (`hi-IN`, `te-IN` or `en-IN`), **never `auto`**, because `auto` reads text with no Indic script as English
- rewrites units to how callers say them, before Timbre reads `kg` as the English "kilograms": `2 kg` becomes "2 kilo", `1 L` becomes "1 litre". It's a small table per language
- leaves ₹ amounts as digits.

Unit tests cover the pre-pass. The smoke test checks Timbre's readings, especially Telugu, which Gnani says is still being refined.

## Switching providers
```
STT_PROVIDER=gnani   TTS_PROVIDER=gnani     # contest default
STT_GNANI_MODEL=prisma-v3.0                 # or empty for v2.5
STT_PROVIDER=sarvam  TTS_PROVIDER=google    # upstream default, for A/B comparison in the eval
```
