# External research

Vendor facts, each with its source and the date it was read. **Docs change fast** (Prisma v3.0 shipped on 2026-10-22, after the brief was written), so re-read the live page before relying on a fact in code.

**Update 2026-11-02:** read the realtime WebSocket pages for STT and TTS in full while writing the backends. Corrections: the `commit` frame is documented on the STT WebSocket page; the headers there are `language_code`, `model`, `format`, `keyterms` (the model page's `lang_code`, `x-model`, ... are the older spellings; both are accepted, new wins); frames are exactly 1,024 bytes, 32 ms at 16 kHz or 64 ms at 8 kHz; sessions last 15 minutes, idle timeout 60 s; TTS supports `sample_rate` 8000 to 48000 and `mulaw`/`alaw` (forced to 8 kHz); TTS speed range is 0.85 to 1.15. See DEC-035. **Checked against the real service the same day:** it sends no `processing` message (the page says it does); `transcript` carries `latency` and (v3.0) `detected_language_code`; `format=transcribe` writes spoken numbers as digits. Groq: this account's chat models are gpt-oss-120b, gpt-oss-20b and qwen3.8-27b (docs also list Llama models, unavailable here); 8,000 tokens a minute and 1,000 requests a day (DEC-038).

**Last verified: 2026-10-28**, against docs.gnani.ai (page index: https://docs.gnani.ai/llms.txt), gnani.ai/internship, PyPI and ai.google.dev.

---

## What changed since the brief (2026-10-26)
| The brief said | The live docs say (2026-10-28) | Effect on us |
|---|---|---|
| Prisma has **no language auto-detect** | **Prisma v3.0** (released 2026-10-22, opt-in with `x-model: prisma-v3.0`) takes `lang_code: indic-auto` or a **list of up to 4 languages** (`hi-IN,en-IN,te-IN`) as hints, not a lock. Every transcript carries `detected_language_code` | Language selection (DEC-005) is mostly solved by the model. See DEC-023 |
| `finish()` must send ~600 ms of silence so the server's VAD closes the segment | v3.0 has a **`commit`** control frame: "Closes the open utterance immediately instead of waiting for silence" | No silence flush, so lower latency. Our webrtcvad decides the end of speech and sends `commit` |
| Word boosting with `x-bias-list`, 100 single words, letters only | v3.0 uses **`x-keyterms`**: up to **200 words or short phrases**, mixed scripts allowed (JSON-escape non-ASCII in headers). `x-bias-score` is ignored on v3.0 | Product names with spaces ("Amul butter", "toor dal") and native-script names can go in |
| Formats: `verbatim` or `transcribe` | v3.0 adds **`codemix`** (English words stay Latin, numbers stay words) and **`transliterate`** (everything in Latin letters) | `codemix` or `transcribe` suits Hinglish orders. Pick in the eval |
| Timbre needs **numbers, dates and currency written as words** | Timbre now runs **text normalisation automatically** on every request: `₹599` becomes "five hundred ninety nine rupees", `2 kg` becomes "two kilograms", lakh grouping, dates, times | Our normaliser becomes a thin safety net, not a full converter. See DEC-024 |
| SDK `gnani-vachana`, Python 3.10+ | **v0.9.0** (2026-10-27); PyPI says Python ≥ 3.9 (the docs say 3.10+). Depends on `requests>=2.28`, `websockets>=12.0` | Pin `gnani-vachana==0.9.0` and `websockets>=12` |
| Gemini `gemini-2.5-flash` | 2.5 models are still served but **only to users who used them before**. Google recommends **`gemini-3.5-flash-lite`** or **`gemini-3.8-flash`** for new projects | A new API key may not get 2.5 Flash. See B-06 and DEC-025 |

---

## The contest (gnani.ai/internship, read 2026-10-28)
- **Timeline:** opened Oct 1, 2026 (one third-party source says Sep 30). **Submissions close Nov 10, 2026, 11:59 PM IST.** Details can be edited until you submit. Internships start **Jan 1, 2027** (six months).
- **Eligibility:** enrolled at an Indian college or university, aged 18+. **Solo or a team of two.**
- **Required:** a working app on at least one Gnani model or API, **shown working in a public video**. Name the models used and each member's contribution.
- **Models the page lists:** Prisma v2.5 (STT, 10+ languages plus Hinglish, Tanglish and Benglish), Timbre v2.5 (TTS, "Beta"), Evon v3.3 (reasoning; open weights on Hugging Face by request; **not on the API**). The page banner also promotes Prisma v3.0. The docs offer Prisma v3.0 and Timbre v3.0 too, so both are fair to use. Say "Prisma v3.0 and Timbre v3.0" in the submission.
- **The demo post** must be on LinkedIn or X (or both), tagged **#GnaniAI** and **#GreatIndianAIInternshipChallenge**, and **live before you submit**. Nominate one post link per platform.
- **Final submission:** demo video, written explanation, the list of Gnani models or APIs, the nominated post links.
- **Shortlist:** eligibility (genuine Gnani use) plus **verified engagement** (reactions, comments, reshares) on the nominated posts, **counted at the closing cutoff**. Then individual interviews.
- **Banned:** bought engagement, bots, paid promotion, engagement swaps, plagiarism, **misleading demos**.
- **Prizes:** up to 100 internships (stipend up to ₹1 lakh a month); **ten awards of ₹50,000**, at most one per entry.
- **Credits:** 5,000 per registration (on the primary registrant's account for teams).
- **The Agent Builder is outside the challenge's scope** (and has no API), so build on the speech APIs.

### All ten awards
| Award | Criterion | For us |
|---|---|---|
| Main Character | Best build in a regional or low-resource Indian language | ✅ Telugu |
| Mixed Vibes | Best code-mixed voice experience (Hinglish, Tanglish, Benglish) | ✅ Hinglish |
| Real Deal | Most useful real-world problem; **kirana stores are named as an example** | ✅ Strong |
| Noise Canceller | Best on messy, noisy, real telephone audio | ✅ Real phone line plus a noisy eval |
| Two-Person Army | Best team of two | ❌ Solo |
| Solo Ninja | Best solo project | ✅ |
| Jugaad Genius | Most creative or unexpected use of Gnani's models | 🟡 Possible: a ₹2k phone plus a Pi as the "telephony stack" is a jugaad story |
| Small Town, Big Build | Best entry from a Tier 2 or 3 town or college | ❓ Depends on Surya's college or city |
| Demo Day Drop | Best 60-second demo video | ✅ |
| Crowd Favourite | Public votes on LinkedIn and X | 🟡 Comes from the same posts |

---

## Prisma: speech-to-text (docs.gnani.ai/api/STT, read 2026-10-28)
### Choosing the model
| | Prisma v2.5 (default) | **Prisma v3.0** |
|---|---|---|
| Select (Realtime) | No `x-model`, or `x-model: gnani-prisma-v2.5` | `x-model: prisma-v3.0` |
| Languages | One `lang_code` | `indic-auto`, or 1–4 comma-separated codes (hints, not a lock) |
| Language reported | No | `detected_language_code` on every transcript with text (from the script of the text) |
| Formats | `verbatim`, `transcribe` | + `codemix`, `transliterate` |
| Hints | `x-bias-list` + `x-bias-score` (100 single words) | `x-keyterms` (200 words or phrases); `x-bias-list` is an alias; score ignored |
| End an utterance now | — | `{"type": "commit"}` |
| Change settings mid-session | Bias and substitution only | Also `language_code`, `format` and keyterms, through `update_settings` (from the next utterance) |

Same languages for both: `bn-IN en-IN gu-IN hi-IN kn-IN ml-IN mr-IN pa-IN ta-IN te-IN`. `en-IN` "accepts English-Hindi mixed audio and generates output in English (Latin script)".

### Realtime WebSocket: `wss://api.vachana.ai/stt/v3/stream`
- Settings go in the **upgrade headers**: `x-api-key-id`, `lang_code` (required except with `transliterate`), `x-model`, `x-sample-rate` (8000, 16000, 44100 or 48000; default 16000), `x-format`, `x-keyterms`, `x-idle-timeout-sec`, `x-api-request-id`, `x-enable-substitution` / `x-substitution-map` (≤ 10 find-and-replace rules).
- **VAD headers** (fixed per connection): `x-vad-threshold` (0.7; telephony 0.65–0.75), `x-min-silence-ms` (500; telephony 400–600), `x-min-speech-ms` (100; raise to 200–300 when noisy), `x-min-segment-ms` (120; too high silently drops "haan" and "yes"), `x-max-speech-s` (off).
- **Audio:** raw s16le mono, **exactly 1,024-byte frames** (32 ms at 16 kHz), **at real-time pace**. Bursts hurt VAD.
- **Server messages:** `connected` (config echo; v3.0 adds `request_id`), `speech_start` (v3.0 adds `utterance_id`), `processing`, `transcript` (`text`, `segment_id` = `<request_id>-seg-<N>`, `segment_index` from 1, `audio_duration_ms`, `latency`; v3.0 adds `detected_language_code`, `utterance_id`, `is_final: true`), `error`, `settings_updated`.
- **Limits:** a session lasts at most **15 min** (then `error` and close 1001). **Idle timeout 60 s** by default with no speech (`x-idle-timeout-sec`, 5–900). The **concurrent-session cap is per organisation**; a rejected connection gets an `error` naming the limit. A bad header closes with 1008. A bad key gets HTTP 401 at the handshake.
- **Numbers on our account:** "Current request-rate and concurrent-session limits for your account are available at app.gnani.ai." **Check after registering.**

### Word boosting and keyterms in headers
Non-ASCII must be JSON-escaped in a header (`["खाता"]`). An invalid bias list is **silently ignored** (no error), so log `settings_updated` or `connected` to confirm. Gnani warns that context can make a model *less* accurate: **compare with and without keyterms on our own audio.**

### REST: `POST https://api.vachana.ai/stt/v3`
Multipart `audio_file`, `language_code`, `model`, `format`. **Clips up to 30 s** (the brief said 60 s). Live limits from `GET /stt/v3/languages`. v3.0 REST also takes `topic`, `previous_text` and `speaker_names`.

---

## Timbre: text-to-speech (docs.gnani.ai/api/TTS, read 2026-10-28)
- **Realtime:** `wss://api.vachana.ai/api/v1/tts`, header `X-API-Key-ID`. One JSON request per text: `text`, `voice`, `model`, `language`, `speed` (0.85–1.15), `audio_config` {`sample_rate` 8000/16000/22050/24000/44100/48000 (default 48000), `num_channels`, `sample_width`, `encoding`, `container` (default `wav`)}. **Ask for `sample_rate: 16000`, `container: raw`**, or you get 48 kHz WAV.
- **Messages:** `start` (`request_id`), `audio` (`data.audio` base64, `data.chunk_index`, `data.is_final`), `complete`, `error` (the connection stays open after recoverable errors).
- **One synthesis request at a time per connection.** The example closes on `complete` "instead of waiting for the idle timeout", so idle connections time out. The idle length isn't documented; measure it, and reconnect or ping.
- **`language`:** `auto` (recommended for mixed content), the 10 `xx-IN` codes, and `hi-en` (Hinglish).
- **Models:** `timbre-v3.0` has **13 voices, each speaking all 10 languages**, plus inline **audio tags** (`<pauses>`, `<laugh>`, `<whispers>`…). `timbre-v2.5` has 42 voices with one preferred language each (Telugu: Suhana, Lehara, Lavanya, Yukti, Varuni; Hinglish: Poorvi; Hindi: Nalini and others). **A voice from one model sent to the other gets 400.**
- **v3.0 voices for us:** female, warm customer service: **Shivani** ("warm, patient, empathy-first voice for inbound customer support"), Kalpana, Tarika, Chetana. Male: Yashraj, Devansh. Shortlist **Shivani** and **Devansh**; choose by ear in the smoke test.
- **Text normalisation (automatic):** numbers, ₹ and `Rs` amounts (lakh grouping, paise), %, dates, times, units (`kg` is "kilograms", `L` is "litres"; units are **always read in English**), ranges (`3–5` is "three to five"), digit-by-digit for IDs (6+ digits, or near "account", "OTP" or "PIN").
  - **Caveats:** English, Hindi, Marathi and Tamil have "the deepest coverage"; **Telugu is "fully supported" but word choices are still being refined.** Under `language: auto`, **text with no Indic script normalises as English** even in an Indic voice, so pass `te-IN` or `hi-IN` explicitly for romanized replies. `hinglish` isn't a valid value (only `hi-en` for v2.5 Poorvi; check it on v3.0).
- **REST:** `POST /api/v1/tts/inference` returns the whole audio. **SSE:** `POST /api/v1/tts/sse`.

## Errors and rate limits (docs.gnani.ai/api/introduction/errors, read 2026-10-28)
- `401` bad key · **`402` insufficient credit** · **`429 RATE_LIMITED`**, for example *"Only 1 active request is allowed at a time"* for accounts limited to one active request. No `Retry-After`; back off (0.5 s, 1 s, 2 s; three tries).
- **Risk:** if contest accounts are limited to **one active request**, then STT and TTS can't overlap, and the recorder's speculative STT sessions will be refused. **Check the limit on app.gnani.ai as soon as the key exists**.
- **Credit cost per second of audio or per character isn't published** in the docs. Measure it from the dashboard in the smoke test.

## Python SDK (PyPI, read 2026-10-28)
`gnani-vachana` **0.9.0** (2026-10-27); earlier 0.8.2 (2026-10-22), 0.8.1 and 0.8.0 (2026-10-06). The STT client doesn't expose the VAD headers, so use raw `websockets` (≥ 12; `additional_headers=` on websockets ≥ 13, `extra_headers=` before that).

## Gemini (ai.google.dev, read 2026-10-28; page updated 2026-10-26)
- **Stable text models:** `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`; Pro only as `gemini-3.1-pro-preview`.
- **`gemini-2.5-flash`:** still served "until further notice", but **only to users who used it before**. New projects should use **3.5 Flash-Lite or 3.8 Flash**.
- **Thinking:** for gemini-3.x, Google's thinking page (ai.google.dev/gemini-api/docs/thinking, read 2026-10-28) documents only `thinking_level`. Lowest levels: `minimal` on 3.5 Flash-Lite and 3.6 Flash, `low` on 3.8 Flash (no `minimal`); gemini-2.5-flash-lite defaults to off. It doesn't mention `thinking_budget` for 3.x, so whether `thinking_budget=0` is refused there is **unknown**; `llm_gemini.py` sends `thinking_level` for 3.x.
- **Rate limits** depend on tier and model and are shown in **AI Studio** ("not guaranteed"). Third-party blogs report the free tier was cut sharply in Dec 2025 and April 2026 (Flash at roughly 20–250 requests a day, depending on the source). **Unverified: read the AI Studio page for our key.** A 20-script eval with ~6 turns each is ~120+ requests, so a low daily cap means spreading the eval over days or enabling billing.

---

## Inherited from upstream research (July–August 2026)
- **Sarvam** concurrency limit: **20 (Starter) / 100 (Pro or Business), account-wide** (docs.sarvam.ai rate limits). A real rejection shows as WebSocket close code **1003**; "Timed out waiting for streaming result" is our own 20 s timeout.
- **Google STT:** `chirp` has no multi-language support in any region; `chirp_2` only in eu, global and us; `latest_long` with en, hi and te only in `global`.
- **Gemini on Vertex:** `gemini-2.5-flash-lite` returned 404 in `asia-south1` for the upstream project.
- **Telephony:** Twilio, Exotel and Plivo were compared for multi-line calling; parked (DEC-019).

## Sources
- Gnani docs index: https://docs.gnani.ai/llms.txt
- Prisma v3.0: https://docs.gnani.ai/api/STT/models/prisma-v3.md
- Models: https://docs.gnani.ai/api/STT/models/overview.md
- Realtime STT: https://docs.gnani.ai/api/STT/stt-websocket.md
- STT limits: https://docs.gnani.ai/api/STT/limits.md
- Changelog: https://docs.gnani.ai/api/introduction/changelog.md
- Realtime TTS: https://docs.gnani.ai/api/TTS/tts-websocket.md
- Voices: https://docs.gnani.ai/api/TTS/available-voices.md
- Text normalisation: https://docs.gnani.ai/api/TTS/tts-input-formating.md
- Errors: https://docs.gnani.ai/api/introduction/errors.md
- Contest: https://www.gnani.ai/internship
- SDK: https://pypi.org/project/gnani-vachana/
- Gemini models: https://ai.google.dev/gemini-api/docs/models
- Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Third-party contest coverage (for cross-checking only): sightsinplus.com, fintechbiznews.com, successcds.net
