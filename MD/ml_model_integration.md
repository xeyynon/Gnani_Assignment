# Integrating Prisma and Timbre

How Gnani's models plug into the existing pipeline. The API facts come from [external_research.md](external_research.md), and the interfaces are in [integration_handoff.md](integration_handoff.md).

## Step 0: smoke test first (`scripts/gnani_smoke_test.py`)
Before touching the pipeline:
1. Stream a 16 kHz WAV to Prisma at real-time pace (1,024-byte frames every 32 ms). Print each `transcript` with its `latency`, `segment_id` and `audio_duration_ms`.
2. Synthesise one Hindi, one Telugu and one Hinglish sentence through Timbre. Write WAVs and time the gap from send to the first `audio` chunk.
3. Note the credits used.
4. Record the results, with the date, in [tried_and_implemented.md](tried_and_implemented.md) or [tried_and_failed.md](tried_and_failed.md).

## Prisma STT (`stt_gnani.py`)
**Connection:** `wss://api.vachana.ai/stt/v3/stream`. Every setting goes in the upgrade headers:
```
x-api-key-id:    <GNANI_API_KEY>
lang_code:       hi-IN | te-IN | en-IN       (required, no auto-detect)
x-sample-rate:   16000
x-format:        transcribe                  (to evaluate against verbatim)
x-vad-threshold: 0.7
x-min-silence-ms: 500                        (to tune; see below)
x-min-speech-ms: 100
x-bias-list:     <product words>             (up to 100 words, letters only)
x-bias-score:    <to tune>
```
Check the exact header format of `x-bias-list` (comma- or space-separated?) against the live docs.

**Threading:** each `StreamingSession` owns a thread running its own asyncio loop, the same shape as `stt_sarvam.py`. `feed()` is called from `recorder_thread` and must never block it.

**Framing:** the recorder hands over 30 ms frames (960 bytes). Keep a buffer and send exact 1,024-byte frames. **Pace them to real time.** In practice they arrive in real time from the mic, so send as they fill rather than burst-sending a backlog.

**Ending a segment:** Prisma decides segment ends with its own VAD; there's no end-of-audio message. Our recorder has already decided the caller stopped (650 ms hangover), so `finish()`:
1. sends ~600 ms of silent 1,024-byte frames (about 19 frames)
2. waits for `processing` and then `transcript`, with a timeout
3. joins every segment's `text` received during the session, in `segment_index` order
4. returns `(text, lang_code)`.

**Latency to watch:** that silence flush adds up to `x-min-silence-ms` on top of our own 650 ms hangover. Measure in the smoke test whether to lower `x-min-silence-ms` (e.g. to 300) or send fewer silence frames.

**Language changes:** `lang_code` is fixed per connection. When the processor's language lock changes, the *next* session opens with the new code. Sessions are already per utterance, so nothing needs to reconnect mid-utterance.

**Bias list:** built from the product names in `companies/dukaan_dost/knowledge/products_pricing.md`: brand names and romanized Hindi and Telugu names (letters only, at most 100). Generate it at startup from the knowledge file so the two can't drift apart.

## Timbre TTS (`tts_gnani.py`)
**Streaming:** `wss://api.vachana.ai/api/v1/tts`, header `X-API-Key-ID`. Send one JSON request per sentence:
```json
{"text": "...", "voice": "<chosen v3.0 voice>", "model": "timbre-v3.0",
 "language": "hi-IN", "speed": 1.0,
 "audio_config": {"sample_rate": 16000, "num_channels": 1, "sample_width": 2,
                  "encoding": "linear_pcm", "container": "raw"}}
```
Receive `start`, then `audio` messages (`data.audio` is base64 PCM), then `complete`. Decode the base64 and yield the raw bytes from `chunks()`.

**Keep the connection warm:** open it in `warmup()` and reuse it. Upstream dropped Sarvam's TTS because opening a fresh connection per sentence made it 40–70% slower to first audio than Google (see [failmlmodel.md](failmlmodel.md)). Don't repeat that.

**One request at a time:** guard the connection with a lock. If barge-in abandons a request, either drain to `complete` in the background or close and reconnect. Measure which is faster.

**`synthesize()`** (used for the greeting and cached replies): `POST https://api.vachana.ai/api/v1/tts/inference` returns WAV. Check it's 16 kHz mono LINEAR16. If not, request that or resample.

**Normaliser:** Timbre reads digits badly, so before every request:
- `₹45`, `Rs 45` or `45 rupees` become "forty-five rupees" (Hindi: "पैंतालीस रुपये"; Telugu: "నలభై ఐదు రూపాయలు")
- quantities like `2 kg`, `500 g` or `1 L` become words, in the target language
- runs of 5 or more digits are spelled out digit by digit (`needs_digit_spelling` already makes this call)

Write it as a pure function with unit tests: it's the part most likely to break the demo.

## Switching providers
```
STT_PROVIDER=gnani   TTS_PROVIDER=gnani     # contest default
STT_PROVIDER=sarvam  TTS_PROVIDER=google    # upstream default, for A/B comparison in the eval
```
