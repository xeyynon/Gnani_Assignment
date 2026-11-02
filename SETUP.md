# Setup and run

Dukaan Dost is software only. It runs on any laptop (Windows, macOS or Linux), and you
place a test call from a browser tab. No phone, Raspberry Pi or special hardware is used.

## 1. Install
Python 3.10 or newer, then from the project root:
```bash
python -m venv .venv
.venv/Scripts/activate            # Windows. On macOS or Linux: source .venv/bin/activate
pip install -r requirements.txt
```
`webrtcvad-wheels` in the requirements installs prebuilt on all three systems.

## 2. Keys
```bash
cp local_config.example.py local_config.py     # gitignored; never commit it
```
Fill in the keys you need:

| Key | When | Get it from |
|---|---|---|
| `GNANI_API_KEY` | `STT_PROVIDER=gnani` and/or `TTS_PROVIDER=gnani` | https://app.gnani.ai/voice |
| `GEMINI_API_KEY` | The language model, with no Google Cloud project needed | https://aistudio.google.com/apikey |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Gemini on Vertex AI, Google STT or TTS (today's default speech providers) | A Google Cloud project with Speech-to-Text, Text-to-Speech and Vertex AI enabled; then `gcloud auth application-default login` |
| `SARVAM_API_KEY` | `STT_PROVIDER=sarvam` (today's default) | https://dashboard.sarvam.ai |

## 3. Run and place a call
From the project root:
```bash
python -m dukaan_dost
```
It prints `Ready: open http://127.0.0.1:8765 in a browser and press Start call`. Open that
address, allow the microphone, and press **Start call**. Use headphones, or the agent hears
itself. Press **Hang up** to end the call. Stop the agent with Ctrl+C.

The microphone only works on `localhost` or over `https`, so to call from another machine put
TLS in front of the server (or use an https tunnel).

Settings you may want (all optional):

| Variable | Default | Meaning |
|---|---|---|
| `SHOP_NAME` | `dukaan_dost` | Which folder under `shops/` to run ([shops/README.md](shops/README.md)) |
| `SHOP_DISPLAY_NAME` | `display_name` in the shop's config.yaml, else the folder name | Overrides the name the greeting speaks for the default shop |
| `ADMIN_PASSWORD` | unset | Password for user `admin` on every shop's dashboard; unset means no admin sign-in |
| `AUDIO_HOST`, `AUDIO_PORT` | `127.0.0.1`, `8765` | Where the call server listens |
| `AUDIO_TRANSPORT` | `websocket` | Where call audio comes from and goes to |
| `CALL_DATA_ENABLED` | `0` | Call recording; leave off (synthetic data only) |
| `LLM_MODEL` | `gemini-3.5-flash-lite` with a Gemini key, else `gemini-2.5-flash` | The language model |

Every other tuning setting (VAD, barge-in, timeouts, providers) is an env var, listed with its
default and reasoning in the CONFIG section at the top of `dukaan_dost/app.py`.

## Shops and the shopkeeper dashboard
Each shop is a folder under `shops/` ([shops/README.md](shops/README.md)). One running agent serves all of them, and the **call link picks the shop**: `/s/<shop>/` for the call page, `/` for the default shop.

Each shop's owner gets a dashboard at `/s/<shop>/dashboard`, protected by a PIN:
```bash
python -m dukaan_dost.auth set-pin <shop>             # asks for a PIN twice; stored hashed in data/auth.json
python -m dukaan_dost.demo_data <shop>                # optional: made-up orders, loans and credit balances to look at
```
Open `http://127.0.0.1:8765/s/<shop>/dashboard`; the browser asks for a password, which is the PIN (the user name is ignored). To oversee any shop, set `ADMIN_PASSWORD` in `local_config.py` and sign in as user `admin`. Wrong guesses lock a shop for a minute after five. Sign-in is HTTP Basic auth, so use `localhost` or `https`.

The agent does not write real orders yet, so until it does the dashboard shows only the demo data, marked as made up.

**To just look at it, with no keys or setup:**
```bash
python -m dukaan_dost.preview        # opens http://127.0.0.1:8765/s/demo_kirana/dashboard, password 1111
```
It serves only the dashboard, with a made-up shop, in a temporary folder that is deleted when you stop it (Ctrl+C).

## Tests (no call needed)
```bash
python -m pytest                     # the offline tests
```
- `tests/manual/` holds two end-to-end checks that need real cloud credentials; run those files directly.
- `evaluation/` holds the benchmark tools ([evaluation/README.md](evaluation/README.md)).

## Using Gnani's speech models
```bash
export GNANI_API_KEY=...            # or put it in local_config.py
export STT_PROVIDER=gnani           # Prisma v3.0 for listening   (default: sarvam)
export TTS_PROVIDER=gnani           # Timbre v3.0 for speaking    (default: google)
python scripts/gnani_smoke_test.py roundtrip     # first contact: Timbre speaks, Prisma listens, scores printed
python -m dukaan_dost
```
The two are independent: Gnani for listening and Google for speaking works. Settings (all optional): `GNANI_STT_MODEL` (default `prisma-v3.0`), `GNANI_STT_FORMAT` (`transcribe`, `verbatim`, `codemix`), `GNANI_STT_LANGUAGES` (default `hi-IN,en-IN,te-IN`), `GNANI_TTS_VOICE` (default `Shivani`), `GNANI_TTS_SPEED`, `GNANI_TTS_LANGUAGE` (e.g. `hi-en` to force Hinglish). This code has been tested only against a stand-in server so far; see B-13.
