# AI Caller

A voice AI agent that answers phone calls, understanding and replying in
Telugu, Hindi, or English (including code-switching) depending on the caller,
and grounding its answers in a pluggable knowledge base via a Gemini-backed
conversation manager. Per-deployment content (name, prompt, knowledge base)
lives under `companies/<name>/` — nothing deployment-specific is hardcoded
into the source.

Runs on a Raspberry Pi, connected to a phone over Bluetooth HFP/SCO (the phone
receives the actual call; the Pi captures/plays audio over that Bluetooth link
via PipeWire).

## Architecture

- **Telephony**: Bluetooth HFP/SCO via PipeWire (`pw-record`/`pw-play`), one
  call at a time. `watchdog_thread` detects call start/end by polling for the
  Bluetooth audio nodes.
- **STT**: Sarvam AI (`saaras:v3`, primary — purpose-built for Indian-language
  and code-switched speech) with Google Cloud STT v2 (`latest_long`, `global`)
  as a fallback/comparison provider. Selected via `STT_PROVIDER` env var,
  dispatched through `companies/core/stt_provider.py`.
- **LLM**: Gemini (`gemini-2.5-flash`) via Vertex AI, streamed
  sentence-by-sentence so TTS can start speaking before the full reply is
  generated (`companies/core/llm_gemini.py`, `conversation_manager.py`).
- **TTS**: Google Cloud Text-to-Speech, streaming synthesis
  (`companies/core/tts_google.py`).
- **Main process**: `ai_caller_final3.py` — five threads (recorder, processor,
  playback, watchdog, loopback guard) coordinating capture, VAD/endpointing,
  the STT→LLM→TTS pipeline, barge-in/interrupt handling, and call-boundary
  isolation.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `local_config.example.py` to `local_config.py` and fill in your own
   `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `SARVAM_API_KEY`.
   `local_config.py` is gitignored — never commit real credentials.
3. Create a `companies/<your-company>/` folder (config.yaml + knowledge/) —
   see `companies/core/` for what the code expects — and point the app at it
   with the `COMPANY_NAME` env var (e.g. `COMPANY_NAME=your-company`).

## Running

See **[RUNNING.md](RUNNING.md)** for the full run/stop commands, why they're
written the way they are, how to run from Thonny, and a troubleshooting table
for the problems most likely to come up (duplicate instances, IP changes,
signal-handling quirks).

Quick version:

```bash
cd "/home/pi/ai-caller"
setsid nohup /usr/bin/python3 ai_caller_final3.py > /tmp/live_test.log 2>&1 < /dev/null &
disown
```

Stop it cleanly: `pkill -f ai_caller_final3.py`.

## Configuration

Most tuning knobs (VAD thresholds, timeouts, STT provider/model/location,
concurrency limits) are environment variables — see the `CONFIG` section near
the top of `ai_caller_final3.py` for the full list with their defaults and the
reasoning behind each value.

## Testing

- `tests/stt_regression_test.py` — replays real captured WAVs (from
  `AI_CALLER_DUMP_DIR`) through the actual STT provider code path, scored by
  word error rate against a small hand-confirmed ground truth.
- `tests/test_stop_e2e.py` — verifies the stop-word capture/recognition path
  offline, without a live call.
- `tests/test_streaming_e2e.py` — verifies the streaming
  Gemini→TTS→validation pipeline offline, without a live call.
- `run_benchmark.py` / `analyze_benchmark.py` — STT accuracy/latency
  benchmark harness and its report generator.
- `stt_diagnose.py` — offline root-cause tool for STT issues: measures the
  real frequency spectrum of captured audio and re-submits it to Google STT
  under several configs side by side.

## Data

- `logs/vad_metrics.csv` — one row per utterance, VAD/endpointing metrics.
  Rotates automatically at 5MB.
- `/home/pi/call_data/` (configurable via `CALL_DATA_DIR`) — one folder
  per call, containing each turn's audio (WAV) and a `manifest.jsonl` pairing
  it with the transcript, detected language, and the bot's reply. Intended as
  training data for a future in-house model. Always on by default
  (`CALL_DATA_ENABLED=0` to disable). Guarded against filling the disk: stops
  recording (call handling continues normally) if free space drops below
  500MB.
