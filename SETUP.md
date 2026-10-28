# Setup and run

The agent can run on a Raspberry Pi paired with a phone over Bluetooth (the only
transport so far). Module-level tests run on any laptop. The Pi guides are
[deploy/INSTALL.md](deploy/INSTALL.md) (new Pi, autostart) and
[deploy/RUNNING.md](deploy/RUNNING.md) (run, stop, troubleshooting).

## 1. Install
On the Pi:
```bash
git clone <this repo> ~/projects/dukaan-dost
cd ~/projects/dukaan-dost
bash deploy/setup_pi.sh        # PipeWire, WirePlumber, BlueZ, a .venv with requirements.txt
```
On a laptop (tests only): Python 3.10+, then `pip install -r requirements.txt`. On Windows
`webrtcvad` needs the prebuilt `webrtcvad-wheels` package instead.

## 2. Keys
```bash
cp local_config.example.py local_config.py     # gitignored; never commit it
```
Fill in the keys you need:

| Key | When | Get it from |
|---|---|---|
| `GNANI_API_KEY` | Gnani STT or TTS (coming in the next builds) | https://app.gnani.ai/voice |
| `GEMINI_API_KEY` | The language model, with no Google Cloud project needed | https://aistudio.google.com/apikey |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Gemini on Vertex AI, Google STT or TTS (today's default speech providers) | A Google Cloud project with Speech-to-Text, Text-to-Speech and Vertex AI enabled; then `gcloud auth application-default login` |
| `SARVAM_API_KEY` | `STT_PROVIDER=sarvam` (today's default) | https://dashboard.sarvam.ai |

## 3. Pair the phone (Pi transport)
```bash
bluetoothctl     # pair, trust and connect the phone that receives the shop's calls
```

## 4. Run
From the project root:
```bash
ps aux | grep dukaan_dost            # make sure it isn't already running
setsid nohup .venv/bin/python3 -m dukaan_dost > /dev/null 2>&1 < /dev/null &
disown
tail -f dukaan_dost.log              # watch it
pkill -f dukaan_dost                 # stop it (under a second)
```
Use the `setsid` form exactly ([MD/decisions.md](MD/decisions.md) DEC-016). Settings you may want:

| Variable | Default | Meaning |
|---|---|---|
| `SHOP_NAME` | `dukaan_dost` | Which folder under `shops/` to run ([shops/README.md](shops/README.md)) |
| `SHOP_DISPLAY_NAME` | derived from `SHOP_NAME` | The name the greeting speaks |
| `AUDIO_TRANSPORT` | `pipewire` | Where call audio comes from and goes to |
| `CALL_DATA_ENABLED` | `0` | Call recording; leave off (synthetic data only) |
| `LLM_MODEL` | `gemini-3.5-flash-lite` with a Gemini key, else `gemini-2.5-flash` | The language model |

Every other tuning setting (VAD, barge-in, timeouts, providers) is an env var, listed with its
default and reasoning in the CONFIG section at the top of `dukaan_dost/app.py`.

## Tests (no call needed)
```bash
python -m pytest                     # the offline tests
```
- `tests/manual/` holds two end-to-end checks that need real cloud credentials; run those files directly.
- `evaluation/` holds the benchmark tools ([evaluation/README.md](evaluation/README.md)).
