"""
envfile.py

Reads KEY=value lines from the project's .env file into the environment, once, when the
package is first imported. It has to run first because some settings (STT_PROVIDER,
TTS_PROVIDER) are read as soon as their modules are imported, before local_config.py is
looked at. .env is gitignored; .env.example shows the names.

Rules, kept deliberately small:
  - blank lines and lines starting with # are skipped; "export KEY=value" is accepted
  - a value may be wrapped in matching single or double quotes; what follows the closing quote
    (a " # comment") is ignored
  - in an unquoted value, a "#" preceded by whitespace starts a comment and is cut off with the
    whitespace before it; a "#" with no space before it stays (a URL fragment, a token)
  - a blank value, or one that still starts with "your-" (the placeholder style used in
    local_config.example.py), counts as not set
  - a variable that is already set in the real environment is never overridden
  - DUKAAN_NO_DOTENV=1 turns the whole thing off (the tests use this)
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _clean(value: str) -> str:
    """The value without its quotes or its trailing comment. `value` still has the space that
    followed the "=", so "A= # note" is seen as a comment and "A=#x" is not."""
    value = value.rstrip()
    if value.lstrip()[:1] in ("\"", "'"):
        value = value.lstrip()
    if value[:1] in ("\"", "'"):
        close = value.find(value[0], 1)
        if close > 0 and (not value[close + 1:].strip() or value[close + 1:].lstrip().startswith("#")):
            return value[1:close]
        if len(value) >= 2 and value[0] == value[-1]:
            return value[1:-1]
        return value
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def parse(text: str) -> dict:
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = _clean(value)
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
