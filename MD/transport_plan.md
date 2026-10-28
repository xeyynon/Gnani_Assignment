# Transport plan: running with no special hardware

**Status:** done as of Build 1002 (DEC-032). The agent is software only. This file records how audio reaches it, the protocol, and what is left to tune.

## What the pipeline needs from a transport
`dukaan_dost/transport.py` defines the interface the pipeline talks to: `start`, `find_call`, `device_name`, `open_capture`, `play`, `stop_playback`, `close`. Audio is 16 kHz mono s16le on the way in and a WAV file per sentence on the way out. Nothing else in the pipeline knows where a call comes from.

## The browser transport (built)
`transport_websocket.py` runs a small server (the `websockets` package) on its own thread. `GET /` serves the call page; `WS /ws` is the call.

| Direction | Message | Meaning |
|---|---|---|
| page → server | binary PCM, any chunk size | microphone audio, 16 kHz mono s16le |
| page → server | `{"type":"played","id":N}` | clip N finished or was stopped |
| server → page | `{"type":"ready"}` | the call is open |
| server → page | `{"type":"busy"}` | another call is in progress; the socket then closes |
| server → page | binary: 4-byte big-endian id, then a WAV file | play this clip |
| server → page | `{"type":"stop"}` | stop playing now (the caller interrupted) |

- A new connection is a new call, with a new key (`web-<id>`).
- `play()` blocks until the page confirms the clip, so the pipeline's timing logic works as before; it gives up after the clip's length plus 5 s.
- Unread microphone audio is capped at the last 10 s.
- The server binds `127.0.0.1` and the microphone needs `localhost` or `https`. For another machine, put TLS in front.

## Settings that were tuned on a Bluetooth line
These were set on the earlier hardware (DEC-009 to DEC-018). They are not wrong, but they are the wrong baseline for clean browser audio. Re-tune one at a time against the evaluation harness, not by feel.

| Setting | Value | Why it may change | Status |
|---|---|---|---|
| `ECHO_TAIL_SEC` | 1.2 s on Bluetooth; **0 by default now** | The browser cancels echo, so the long mute isn't needed | Default changed; effect not measured |
| Mic held back while the agent speaks (`_playing`) | on | The browser keeps the mic open, so true speak-over is possible if this is relaxed | To do, with measurements |
| `BARGE_IN_*` thresholds, pitch check | tuned to tell echo from a caller | Mostly unnecessary without echo; keep the pitch check as a safeguard | To do |
| `VAD_HANGOVER_MS` | 650 | Clean audio may allow less, a direct latency saving | To do: sweep 350–650 ms against time to first audio |
| `VAD_ENERGY_THRESHOLD`, `VAD_MODE` | Bluetooth noise floor | Different gain and noise floor | To do |
| `GREETING_DELAY_SEC` | 0.3 s default now (was 1.0 s) | No link to wait for | Default changed |
| Prisma VAD headers | defaults | Our own VAD decides the end of speech and sends `commit` (DEC-023) | With the Gnani integration |
| Gaps between sentence clips | unknown | The next clip waits for the page to confirm the last (B-09) | To measure |

## What the software-only build gives up, and how to stay honest
- **No real phone call.** The README and posts say "browser call". Phone-line audio is covered by evaluating on simulated phone audio (8 kHz, µ-law, added noise at ~10 dB SNR), labelled as simulated.
- **Cleaner audio than a phone line,** so a browser demo can look better than a real call would. Evaluate on the degraded audio.
- The earlier hardware was the only setup proven on real calls. The browser transport has been tested offline only (B-08).

## Next transports
1. **`ReplayTransport`**: feeds recorded or synthetic caller audio through the whole pipeline with no browser, and captures the reply audio and timings. This is how the evaluation (20 scripts, clean and noisy) runs.
2. **A phone-number transport** (stretch): a provider streams a call's audio over a WebSocket, typically 8 kHz µ-law, so it needs conversion at the transport's edge. Indian-number paperwork was not verified (see the research in [external_research.md](external_research.md)).

## Sources
- LiveKit and Pipecat plugins for Gnani, for reference only: https://docs.gnani.ai/livekit/introduction.md, https://docs.gnani.ai/pipecat/introduction.md
- Twilio India rules: https://www.twilio.com/en-us/guidelines/in/regulatory
