"""
envfile.py

Reads KEY=value lines from the project's .env file into the environment, once, when the
package is first imported. It has to run first because some settings (STT_PROVIDER,
TTS_PROVIDER) are read as soon as their modules are imported, before local_config.py is
looked at. .env is gitignored; .env.example shows the names.

Rules, kept deliberately small:
  - blank lines and lines starting with # are skipped; "export KEY=value" is accepted
  - a value may be wrapped in matching single or double quotes
  - a blank value, or one that still starts with "your-" (the placeholder style used in
    local_config.example.py), counts as not set
  - a variable that is already set in the real environment is never overridden
  - DUKAAN_NO_DOTENV=1 turns the whole thing off (the tests use this)
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse(text: str) -> dict:
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not key.replace("_", "").isalnum() or not value or value.startswith("your-"):
            continue
        values[key] = value
    return values


def load(path=None, environ=None) -> list:
    """Puts the values from the .env file into `environ` (default os.environ) without
    overriding anything already set. Returns the names that were set."""
    environ = os.environ if environ is None else environ
    if environ.get("DUKAAN_NO_DOTENV") == "1":
        return []
    path = Path(path) if path else PROJECT_ROOT / ".env"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    loaded = []
    for key, value in parse(text).items():
        if key not in environ:
            environ[key] = value
            loaded.append(key)
    return loaded
