"""
Offline tests for the startup credential check (bug B-01).

    python -m pytest tests/test_startup_checks.py
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:   # e.g. webrtcvad missing on this machine
        pytest.skip(f"main module not importable here: {e}")
    return m


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)


def test_an_api_key_is_enough(app, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "abc123")
    assert app._gemini_credentials_ok()


def test_a_real_project_is_enough_for_vertex(app, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-real-project")
    assert app._gemini_credentials_ok()


@pytest.mark.parametrize("project", [
    "your-project-id-here",              # the placeholder in app.py
    "your-project-id-or-number-here",    # the placeholder in local_config.example.py (B-01)
    "",                                  # set but empty
    "   ",
])
def test_placeholders_and_empty_projects_are_rejected(app, monkeypatch, project):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", project)
    assert not app._gemini_credentials_ok()


def test_nothing_set_is_rejected(app):
    assert not app._gemini_credentials_ok()


def test_a_placeholder_api_key_does_not_count(app, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your-gemini-api-key-here")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "your-project-id-here")
    assert not app._gemini_credentials_ok()


# ---- speech provider keys -------------------------------------------------------

def test_gnani_without_a_key_is_reported(app, monkeypatch):
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    monkeypatch.setattr(app, "_STT_PROVIDER", "gnani")
    monkeypatch.setattr(app, "_TTS_PROVIDER", "google")
    assert "GNANI_API_KEY" in app._speech_key_problem()
    monkeypatch.setattr(app, "_STT_PROVIDER", "google")
    monkeypatch.setattr(app, "_TTS_PROVIDER", "gnani")
    assert "GNANI_API_KEY" in app._speech_key_problem()


def test_gnani_with_a_key_is_fine(app, monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "abc")
    monkeypatch.setattr(app, "_STT_PROVIDER", "gnani")
    monkeypatch.setattr(app, "_TTS_PROVIDER", "gnani")
    assert app._speech_key_problem() is None


def test_sarvam_without_a_key_is_reported(app, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.setattr(app, "_STT_PROVIDER", "sarvam")
    monkeypatch.setattr(app, "_TTS_PROVIDER", "google")
    assert "SARVAM_API_KEY" in app._speech_key_problem()
