# Tried and failed

Approaches (not models; see [failmlmodel.md](failmlmodel.md) for those) that didn't work. Most come from the earlier project. Add new ones with a date.

| When | What we tried | What went wrong | What we do instead |
|---|---|---|---|
| Jul 2026 | Raising Sarvam concurrency by guessing (1, then 2, then 4) | Each real-call test still showed waits of up to 8 s and 20 s timeouts | Read the vendor's documented limit, set 10 with headroom (DEC-012) |
| Jul 2026 | Locking the call language on the first utterance | "Hello" locked Telugu and Hindi callers into English | Skip bare "hello", "hi", "hey" (DEC-013) |
| Jul 2026 | Detecting language from romanized keywords only | Native-script Telugu (e.g. కావాలి) wasn't recognised as a language signal | Unicode-range script detection, which can re-lock (DEC-014) |
| Jul 2026 | A 500 ms VAD hangover | Natural pauses split one utterance into several fragments | 650 ms (DEC-010) |
| Jul 2026 | Opening an STT session on the first speech-like frame | Single 30 ms noise spikes opened sessions and starved concurrency | Two-frame onset confirmation (DEC-011) |
| Jul 2026 | Running in the background with `&` or `| tee` | The shell could send the process a shutdown signal | `setsid nohup … < /dev/null &` (DEC-016) |
| Jul 2026 | Flagging `google-cloud-bigquery` and `-storage` as unused (grepping imports) | They're required by `google-cloud-aiplatform` | Check with `pip show` before removing anything (DEC-017) |
| Jul 2026 | An STT benchmark with every language voiced by one en-IN TTS voice | The Hindi and Telugu clips were spoken with English phonetics, so the language results meant nothing and the WER was inflated by TTS mispronunciation | **Synthesise each eval script in its own language**; add real recordings |
| Aug 2026 | Logging background stdout to `/tmp/live_test.log` | `/tmp` is RAM-backed on the Pi; the file grew without limit | `/dev/null`, plus the rotating `dukaan_dost.log` (DEC-015) |
| Aug 2026 | Splitting TTS audio internally into a prefix and the rest | Left dead air mid-sentence | Split the *text* at the first comma and play the pieces back to back (DEC-018) |
| Aug 2026 | Sarvam Bulbul TTS | 40–70% slower to first audio | See [failmlmodel.md](failmlmodel.md) |

## Considered and deliberately not built
- **An always-on keyword spotter with AEC for true mid-sentence interrupts:** risks reopening Bluetooth echo bugs (DEC-009).
- **Cloud telephony for multiple lines:** no need for it (DEC-019).
