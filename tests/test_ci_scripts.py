"""
Tests that the CI helper scripts actually fail when they should. A hygiene check
that can never fail is worse than none, because it looks like protection.

    python -m pytest tests/test_ci_scripts.py
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_repo = load("check_repo")
check_docs = load("check_docs")
release_notes = load("release_notes")


# ---- check_repo: secrets ---------------------------------------------------
# The fake keys are assembled at run time so this file does not trip the scanner itself.

def scan(tmp_path, monkeypatch, text, name="x.py"):
    (tmp_path / name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(check_repo, "ROOT", tmp_path)
    return check_repo.check_secrets([name])


@pytest.mark.parametrize("secret", [
    "AIza" + "A" * 35,
    "ghp_" + "b" * 36,
    "AKIA" + "C" * 16,
    "-----BEGIN " + "PRIVATE KEY-----",
    "api_key = '" + "d" * 30 + "'",
])
def test_real_looking_secrets_are_caught(tmp_path, monkeypatch, secret):
    assert scan(tmp_path, monkeypatch, f"value = '{secret}'\n" if "=" not in secret else secret + "\n")


@pytest.mark.parametrize("fine", [
    "GEMINI_API_KEY = 'your-gemini-api-key-here'",
    "api_key = os.environ['GEMINI_API_KEY']",
    "token = 'fake-token-for-tests-1234567890abc'",
    "password = '<password>'",
])
def test_placeholders_and_lookups_are_not_flagged(tmp_path, monkeypatch, fine):
    assert scan(tmp_path, monkeypatch, fine + "\n") == []


# ---- check_repo: files that must stay local --------------------------------

@pytest.mark.parametrize("path", [
    "local_config.py", ".env", "dukaan_dost.log", "logs/vad_metrics.csv", "call_data/x/a.wav",
    "orders/20261101-1.json", "evaluation/audio/clean/a.wav",
])
def test_local_only_files_are_rejected(path):
    assert check_repo.check_forbidden_files([path])


@pytest.mark.parametrize("path", [
    "local_config.example.py", "orders/samples/a.json", "evaluation/results/r.json", "dukaan_dost/app.py",
])
def test_normal_files_are_allowed(path):
    assert check_repo.check_forbidden_files([path]) == []


# ---- check_repo: banned names and commit titles ----------------------------

def test_banned_terms_are_found_in_tracked_files(monkeypatch):
    monkeypatch.setenv("BANNED_TERMS", "dukaan")
    problems, configured = check_repo.check_banned_terms(["README.md"])
    assert configured and problems


def test_banned_terms_do_nothing_when_not_configured(monkeypatch):
    monkeypatch.delenv("BANNED_TERMS", raising=False)
    assert check_repo.check_banned_terms(["README.md"]) == ([], False)


def test_banned_terms_catch_a_name_in_a_file_name(monkeypatch):
    monkeypatch.setenv("BANNED_TERMS", "zzz-secret-name")
    problems, _ = check_repo.check_banned_terms(["docs/zzz-secret-name.md"])
    assert problems


@pytest.mark.parametrize("title, bad", [
    ("Run as software only (Build 1002)", True),
    ("Run as software only ( build 7 )", True),
    ("InBul12: Add CI", False),
    ("Run as software only: call from a browser", False),
])
def test_build_numbers_in_titles_are_rejected(title, bad):
    assert bool(check_repo.BUILD_IN_TITLE.search(title)) is bad


def test_the_repository_passes_its_own_checks():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_repo.py")],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout


# ---- check_docs ------------------------------------------------------------

def links_in(tmp_path, markdown, extra_files=()):
    for name in extra_files:
        (tmp_path / name).write_text("x", encoding="utf-8")
    md = tmp_path / "doc.md"
    md.write_text(markdown, encoding="utf-8")
    check_docs.ROOT = tmp_path
    return list(check_docs.broken_links(md))


def test_a_broken_relative_link_is_reported(tmp_path):
    assert links_in(tmp_path, "See [other](missing.md).\n")


def test_good_links_anchors_and_web_links_pass(tmp_path):
    md = "[a](other.md) [b](other.md#section) [c](#here) [d](https://example.com/x) [e](mailto:a@b.c)\n"
    assert links_in(tmp_path, md, extra_files=["other.md"]) == []


def test_links_inside_code_are_ignored(tmp_path):
    md = "```\n[x](nope.md)\n```\nand `[y](nope2.md)` inline\n"
    assert links_in(tmp_path, md) == []


def test_every_link_in_the_project_docs_resolves():
    check_docs.ROOT = ROOT
    problems = [(md.name, t) for md in check_docs.markdown_files() for _, t in check_docs.broken_links(md)]
    assert problems == []


# ---- release_notes ---------------------------------------------------------

def test_release_notes_use_the_hand_written_part_only():
    notes = release_notes.notes_for("build-1002")
    assert "### What changed" in notes and "### How it was verified" in notes
    assert "Files changed" not in notes
    assert notes.rstrip().endswith("`MD/builds/build-1002.md`")


@pytest.mark.parametrize("tag", ["InBul12", "build-abc", "v1.0", "build-9999"])
def test_release_notes_reject_non_build_tags_and_missing_reports(tag):
    with pytest.raises(SystemExit):
        release_notes.notes_for(tag)
