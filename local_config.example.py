# Copy this file to local_config.py and fill in your own values —
# local_config.py is gitignored, so it's never shared/committed.
# A value left as a "your-..." placeholder counts as not set.
#
# Dukaan Dost needs, at minimum:
#   - GNANI_API_KEY  (Prisma speech-to-text, Timbre text-to-speech)
#   - GEMINI_API_KEY (the language model; no Google Cloud project needed)
# The Google Cloud project and Sarvam key are only for the comparison
# providers (STT_PROVIDER=sarvam|google, TTS_PROVIDER=google) and for
# running Gemini through Vertex AI instead of an API key.

# Gnani: register at https://www.gnani.ai/internship, then get the key
# at https://app.gnani.ai/voice (5,000 credits on registration).
GNANI_API_KEY = "your-gnani-api-key-here"

# Google AI Studio: https://aistudio.google.com/apikey
# Check your key's rate limits in AI Studio before running the evaluation.
GEMINI_API_KEY = "your-gemini-api-key-here"

# Password for the admin dashboard (user name "admin"). Leave it as the placeholder and
# nobody can sign in as admin. Shop PINs are set separately:
#   python -m dukaan_dost.auth set-pin <shop>
ADMIN_PASSWORD = "your-admin-password-here"

# --- Optional: Gemini through Vertex AI, and the Google STT/TTS providers ---
# Used when GEMINI_API_KEY is not set, or when STT_PROVIDER=google or
# TTS_PROVIDER=google. Setup:
#   1. gcloud auth login
#   2. gcloud auth application-default login
#   3. In your Google Cloud project, enable:
#        Cloud Speech-to-Text API, Cloud Text-to-Speech API,
#        Vertex AI API (aiplatform.googleapis.com)
#   4. Fill in your own project ID/number and a region close to you.
GOOGLE_CLOUD_PROJECT = "your-project-id-or-number-here"
GOOGLE_CLOUD_LOCATION = "asia-south1"  # pick the region closest to you

# --- Optional: Sarvam, the comparison STT provider (STT_PROVIDER=sarvam) ---
# From https://dashboard.sarvam.ai
SARVAM_API_KEY = "your-sarvam-api-key-here"
