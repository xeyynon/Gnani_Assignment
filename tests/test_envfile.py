"""
Tests for the .env loader.

    python -m pytest tests/test_envfile.py
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import envfile  # noqa: E402


def test_keys_and_values_are_read():
    text = "GNANI_API_KEY=abc123\nSTT_PROVIDER=gnani\n"
    assert envfile.parse(text) == {"GNANI_API_KEY": "abc123", "STT_PROVIDER": "gnani"}


def test_comments_blank_lines_export_and_quotes():
    text = "# a comment\n\nexport A=1\nB=\"two words\"\nC='x'\n  D = spaced  \n"
    assert envfile.parse(text) == {"A": "1", "B": "two words", "C": "x", "D": "spaced"}


@pytest.mark.parametrize("line", ["GNANI_API_KEY=", "GNANI_API_KEY=your-gnani-api-key-here", "NOEQUALS", "=value",
                                  "BAD KEY=1", "K-1=2"])
def test_blank_placeholder_and_malformed_lines_are_not_set(line):
    assert envfile.parse(line) == {}


def test_a_value_may_contain_an_equals_sign():
    assert envfile.parse("TOKEN=a=b=c") == {"TOKEN": "a=b=c"}


def test_load_sets_new_names_and_never_overrides(tmp_path):
    f = tmp_path / ".env"
    f.write_text("NEW_ONE=from-file\nALREADY=from-file\n", encoding="utf-8")
    environ = {"ALREADY": "from-shell"}
    assert envfile.load(f, environ) == ["NEW_ONE"]
    assert environ == {"ALREADY": "from-shell", "NEW_ONE": "from-file"}


def test_a_missing_file_is_fine(tmp_path):
    assert envfile.load(tmp_path / "nope", {}) == []


def test_a_file_saved_with_a_byte_order_mark_still_works(tmp_path):
    f = tmp_path / ".env"
    f.write_bytes(b"\xef\xbb\xbfGNANI_API_KEY=abc\n")             # what Windows Notepad can write
    environ = {}
    envfile.load(f, environ)
    assert environ == {"GNANI_API_KEY": "abc"}


def test_the_switch_turns_loading_off(tmp_path):
    f = tmp_path / ".env"
    f.write_text("A=1\n", encoding="utf-8")
    environ = {"DUKAAN_NO_DOTENV": "1"}
    assert envfile.load(f, environ) == []
    assert "A" not in environ


def test_importing_the_package_reads_the_projects_env_file(tmp_path):
    """End to end in a fresh interpreter, because the loader runs at first import."""
    code = ("import os, sys; sys.path.insert(0, %r); import dukaan_dost; "
            "print(os.environ.get('STT_PROVIDER'))" % str(ROOT))
    env_file = ROOT / ".env"
    existed = env_file.exists()
    backup = env_file.read_bytes() if existed else None
    try:
        env_file.write_text("STT_PROVIDER=gnani\n", encoding="utf-8")
        clean = {k: v for k, v in __import__("os").environ.items() if k not in ("STT_PROVIDER", "DUKAAN_NO_DOTENV")}
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=clean)
        assert out.stdout.strip() == "gnani", out.stderr
    finally:
        if existed:
            env_file.write_bytes(backup)
        else:
            env_file.unlink()
