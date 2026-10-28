# Setup and run

The agent runs on a Raspberry Pi paired with a phone over Bluetooth. Module-level tests also run on a laptop. The Pi's full guides are [deploy/INSTALL.md](deploy/INSTALL.md) (new Pi, autostart) and [RUNNING.md](RUNNING.md) (run, stop, troubleshooting).

## 1. Install
On the Pi:
```bash
git clone <this repo> ~/projects/dukaan-dost
cd ~/projects/dukaan-dost
bash deploy/setup_pi.sh        # PipeWire, WirePlumber, BlueZ, a .venv with requirements.txt
```
On a laptop (tests only): Python 3.10+, then `pip install -r requirements.txt`.

## 2. Keys
```bash
cp local_config.example.py local_config.py     # gitignored; never commit it
```
Fill in the keys you need:

| Key | When | Get it from |
|---|---|---|
| `GNANI_API_KEY` | Gnani STT or TTS (coming in the next builds) | https://app.gnani.ai/voice |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Gemini on Vertex AI, Google STT or TTS (today's default) | A Google Cloud project with Speech-to-Text, Text-to-Speech and Vertex AI enabled; then `gcloud auth application-default login` |
| `SARVAM_API_KEY` | `STT_PROVIDER=sarvam` (today's default) | https://dashboard.sarvam.ai |

A Gemini API key (`GEMINI_API_KEY`, no Google Cloud project needed) is planned; see [MD/tasks.md](MD/tasks.md).

## 3. Pair the phone
```bash
bluetoothctl     # pair, trust and connect the phone that receives the shop's calls
```

## 4. Choose the shop and run
```bash
export COMPANY_NAME=dukaan_dost      # folder under companies/ (being built)
export CALL_DATA_ENABLED=0           # never record calls in this project

ps aux | grep ai_caller_final3       # make sure it isn't already running
setsid nohup .venv/bin/python3 ai_caller_final3.py > /dev/null 2>&1 < /dev/null &
disown
tail -f ai_caller.log                # watch it
pkill -f ai_caller_final3.py         # stop it (under a second)
```
Use the `setsid` form exactly. Simpler forms let the shell kill the process ([MD/decisions.md](MD/decisions.md) DEC-016).

## 5. Tune
Every tuning setting (VAD, barge-in, timeouts, providers) is an env var, listed with its default and reasoning in the CONFIG section at the top of `ai_caller_final3.py`.

## Tests (no call needed)
- `tests/test_streaming_e2e.py`: conversation, then validation, then TTS.
- `tests/test_stop_e2e.py`: the "stop" word path.
- `run_benchmark.py` / `analyze_benchmark.py`: the STT benchmark and its report.
