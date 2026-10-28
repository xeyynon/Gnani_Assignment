# Deployment

The full Pi instructions are in [../deploy/RUNNING.md](../deploy/RUNNING.md) and [../deploy/INSTALL.md](../deploy/INSTALL.md). This page is the summary, plus what changes for Dukaan Dost.

## Hardware
- A Raspberry Pi with PipeWire, WirePlumber and BlueZ.
- One Android phone with a SIM. It takes the real call and is paired and trusted with the Pi over Bluetooth HFP. The Pi captures and plays the call audio at 16 kHz mono.

## First-time setup (Pi)
```bash
git clone <this repo> ~/projects/dukaan-dost && cd ~/projects/dukaan-dost
bash deploy/setup_pi.sh          # system packages, .venv, copies local_config.example.py
nano local_config.py             # fill in keys (see below)
bluetoothctl                     # pair and trust the phone
```
For Dukaan Dost, **skip the `gcloud auth` steps** if you're using `GEMINI_API_KEY`. They're only needed on the Vertex path.

## Keys (`local_config.py`, gitignored)
| Key | Needed when | Where to get it |
|---|---|---|
| `GNANI_API_KEY` | `STT_PROVIDER=gnani` or `TTS_PROVIDER=gnani` | https://app.gnani.ai/voice (5,000 credits on registration) |
| `GEMINI_API_KEY` | Always, unless you're using Vertex | Google AI Studio |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Vertex path, Google STT or Google TTS | A Google Cloud project with Speech, TTS and Vertex AI enabled |
| `SARVAM_API_KEY` | `STT_PROVIDER=sarvam` (baseline only) | dashboard.sarvam.ai |

Env vars override nothing that's already set: the code loads `local_config.py` values with `os.environ.setdefault`, so an env var set beforehand wins.

## Environment for the contest
```bash
export SHOP_NAME=dukaan_dost
export STT_PROVIDER=gnani
export TTS_PROVIDER=gnani
export CALL_DATA_ENABLED=0
```

## Run, watch, stop (from RUNNING.md)
```bash
ps aux | grep dukaan_dost                      # make sure it isn't already running (two instances = bot talks over itself)
setsid nohup .venv/bin/python3 -m dukaan_dost > /dev/null 2>&1 < /dev/null &
disown
tail -f dukaan_dost.log
pkill -f dukaan_dost                        # clean stop, under 1 s
```
Use the `setsid` form exactly (DEC-016). For autostart on boot, see Stage 2 in `deploy/INSTALL.md` (a user systemd service plus `loginctl enable-linger`).

## Troubleshooting (inherited)
| Symptom | Likely cause |
|---|---|
| The bot talks over itself | Two instances running |
| Can't SSH to the Pi | Its DHCP address changed; check `hostname -I` on the Pi |
| `ModuleNotFoundError` | Dependencies not installed in the interpreter you used; use the project's `.venv` |
| No audio at call start | The Bluetooth nodes aren't up yet; the greeting waits `GREETING_DELAY_SEC` |
