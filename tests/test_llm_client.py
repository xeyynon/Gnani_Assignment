"""
Offline tests for how llm_gemini picks its client and thinking config.
No network and no real keys: genai.Client is replaced with a recorder.

    python -m pytest tests/test_llm_client.py
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import llm_gemini  # noqa: E402


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("GEMINI_API_KEY", "LLM_THINKING_LEVEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(llm_gemini, "_client", None)


@pytest.fixture
def fake_client(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_gemini.genai, "Client", lambda **kw: calls.append(kw) or object())
    return calls


def test_api_key_unset_means_empty():
    assert llm_gemini.api_key() == ""


def test_api_key_placeholder_counts_as_unset(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your-gemini-api-key-here")
    assert llm_gemini.api_key() == ""


def test_api_key_is_stripped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "  abc123 \n")
    assert llm_gemini.api_key() == "abc123"


def test_api_key_path_builds_a_developer_api_client(monkeypatch, fake_client):
    monkeypatch.setenv("GEMINI_API_KEY", "abc123")
    llm_gemini._get_client()
    assert fake_client == [{"api_key": "abc123"}]


def test_without_a_key_it_uses_vertex(monkeypatch, fake_client):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
    llm_gemini._get_client()
    assert fake_client == [{"vertexai": True, "project": "my-project", "location": "asia-south1"}]


def test_client_is_built_once(monkeypatch, fake_client):
    monkeypatch.setenv("GEMINI_API_KEY", "abc123")
    first = llm_gemini._get_client()
    assert llm_gemini._get_client() is first
    assert len(fake_client) == 1


def test_gemini_2_5_switches_thinking_off_with_a_budget():
    cfg = llm_gemini._thinking_config("gemini-2.5-flash")
    assert cfg.thinking_budget == 0
    assert cfg.thinking_level is None


@pytest.mark.parametrize("model, level", [
    ("gemini-3.5-flash-lite", "MINIMAL"),
    ("gemini-3.6-flash", "MINIMAL"),
    ("gemini-3.8-flash", "LOW"),  # 3.8 Flash has no "minimal" level
])
def test_gemini_3_uses_the_lowest_documented_level(model, level):
    cfg = llm_gemini._thinking_config(model)
    assert cfg.thinking_level.name == level
    assert cfg.thinking_budget is None


def test_thinking_level_can_be_overridden(monkeypatch):
    monkeypatch.setenv("LLM_THINKING_LEVEL", "medium")
    assert llm_gemini._thinking_config("gemini-3.5-flash-lite").thinking_level.name == "MEDIUM"


def test_invalid_thinking_level_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("LLM_THINKING_LEVEL", "banana")
    assert llm_gemini._thinking_config("gemini-3.5-flash-lite").thinking_level.name == "MINIMAL"


def test_make_config_carries_the_models_thinking_config():
    cfg = llm_gemini._make_config("gemini-3.8-flash", 100, 0.5)
    assert cfg.max_output_tokens == 100
    assert cfg.thinking_config.thinking_level.name == "LOW"
