# Deployment

Dukaan Dost is software only. There is no hardware to set up: Python, the keys, and a browser.

## Run it
```bash
python -m venv .venv && .venv/Scripts/activate      # macOS or Linux: source .venv/bin/activate
pip install -r requirements.txt
cp local_config.example.py local_config.py          # then put your keys in it
python -m dukaan_dost
```
Open the address it prints (`http://127.0.0.1:8765` by default), allow the microphone, press **Start call**. See [../SETUP.md](../SETUP.md) for every setting.

## Keys (`local_config.py`, gitignored)
| Key | Needed when | Where to get it |
|---|---|---|
| `GNANI_API_KEY` | `STT_PROVIDER=gnani` or `TTS_PROVIDER=gnani` | https://app.gnani.ai/voice (5,000 credits on registration) |
| `GEMINI_API_KEY` | Always, unless you use Vertex | Google AI Studio |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Vertex path, Google STT or Google TTS | A Google Cloud project with Speech, TTS and Vertex AI enabled |
| `SARVAM_API_KEY` | `STT_PROVIDER=sarvam` (baseline only) | dashboard.sarvam.ai |

Env vars set beforehand win: the code loads `local_config.py` values with `os.environ.setdefault`.

## Environment for the contest
```bash
export STT_PROVIDER=gnani
export TTS_PROVIDER=gnani
export CALL_DATA_ENABLED=0
```

## Running it somewhere else
- The server listens on `127.0.0.1` only. To call from another machine, set `AUDIO_HOST`, and put TLS in front: browsers only give microphone access to `localhost` or `https` pages.
- One call at a time. A second browser is told the line is busy.
- The agent writes `dukaan_dost.log` (size-capped, rotating) in the project root. Calls are never recorded unless `CALL_DATA_ENABLED=1`.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| `Could not start the call server on 127.0.0.1:8765` | Another copy is running, or the port is taken. Set `AUDIO_PORT` |
| The page says it cannot reach the agent | The agent isn't running, or you opened the page from a different address |
| Microphone permission denied | Allow it in the browser's address bar; the page must be on `localhost` or `https` |
| The agent talks over itself or answers its own voice | Use headphones |
| `No Gemini credentials configured` | Set `GEMINI_API_KEY`, or a real `GOOGLE_CLOUD_PROJECT` |
| `Shop folder not found` | `shops/dukaan_dost/` isn't written yet, or `SHOP_NAME` points at a missing folder |
