# Dukaan Dost as a container: the call page and the agent on port 8765.
#
#   docker build -t dukaan-dost .
#   docker run --rm -p 127.0.0.1:8765:8765 \
#     -e GEMINI_API_KEY=... -e GNANI_API_KEY=... -e SARVAM_API_KEY=... dukaan-dost
#
# then open http://localhost:8765 and press Start call. Publishing the port on
# 127.0.0.1 only keeps the agent off your network; browsers also only give
# microphone access to localhost or https pages.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUDIO_HOST=0.0.0.0 \
    CALL_DATA_ENABLED=0

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY dukaan_dost ./dukaan_dost
COPY shops ./shops

# The agent writes dukaan_dost.log next to the code, so the app user owns /app.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8765
CMD ["python", "-m", "dukaan_dost"]
