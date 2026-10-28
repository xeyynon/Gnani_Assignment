#!/usr/bin/env python3
"""
Repository hygiene checks, run by CI and runnable locally:

    python scripts/check_repo.py

Fails (exit 1) when a tracked file or a commit title breaks one of the project
rules:
  R-1   no keys or other secrets committed
  R-3   no customer names. Which names is configured OUTSIDE the repo, in the
        BANNED_TERMS environment variable (comma separated), so the names
        themselves are never committed. CI reads it from a repository variable.
  R-9   no "(Build N)" in a commit title; the tag carries the number
Also fails if a file that must stay local is tracked (local_config.py, .env,
logs, recorded calls, orders).
"""

import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_TRACKED = [
    "local_config.py", ".env", ".env.*", "*.log", "*.log.*",
    "call_data/*", "stt_dumps/*", "logs/*", "evaluation/audio/*",
]
ALLOWED_TRACKED = [".env.example"]
ORDERS_GLOB = "orders/*"
ORDERS_ALLOWED = "orders/samples/*"

SECRET_PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "GitHub token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|github_pat_[A-Za-z0-9_]{50,}"),
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    "key assigned in code": re.compile(
        r"""(?ix)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*["']
            (?!your-|<|\$|\{|fake|test|dummy|example|changeme|xxx)
            [A-Za-z0-9_\-]{24,}["']"""),
}

TEXT_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml", ".toml", ".json", ".html", ".js", ".mjs",
                 ".sh", ".cfg", ".ini", ".service", ""}


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def tracked_files() -> list:
    return [f for f in git("ls-files").splitlines() if f]


def check_forbidden_files(files):
    problems = []
    for f in files:
        name = Path(f).name
        if f in ALLOWED_TRACKED or name in ALLOWED_TRACKED:
            continue
        if fnmatch.fnmatch(f, ORDERS_GLOB) and not fnmatch.fnmatch(f, ORDERS_ALLOWED):
            problems.append(f"{f}: orders are written at run time and stay local (samples go in orders/samples/)")
            continue
        if any(fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(name, pat) for pat in FORBIDDEN_TRACKED):
            problems.append(f"{f}: this kind of file must stay local and gitignored")
    return problems


def readable_text(path: Path):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def check_secrets(files):
    problems = []
    for f in files:
        text = readable_text(ROOT / f)
        if text is None:
            continue
        for label, pat in SECRET_PATTERNS.items():
            m = pat.search(text)
            if m:
                line_no = text.count("\n", 0, m.start()) + 1
                problems.append(f"{f}:{line_no}: looks like a {label}")
    return problems


def banned_terms():
    raw = os.environ.get("BANNED_TERMS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def check_banned_terms(files):
    terms = banned_terms()
    if not terms:
        return [], False
    problems = []
    pats = [(t, re.compile(re.escape(t), re.I)) for t in terms]
    for f in files:
        hay = [f]
        text = readable_text(ROOT / f)
        if text is not None:
            hay.append(text)
        for t, pat in pats:
            if any(pat.search(h) for h in hay):
                problems.append(f"{f}: contains a name from BANNED_TERMS (rule R-3)")
                break
    for t, pat in pats:
        log = git("log", "--format=%H %s%n%b")
        if pat.search(log):
            problems.append("a commit message contains a name from BANNED_TERMS (rule R-3)")
            break
    return problems, True


BUILD_IN_TITLE = re.compile(r"\(\s*build\s+\d+\s*\)", re.I)


def check_commit_titles():
    problems = []
    for line in git("log", "--format=%h %s").splitlines():
        sha, _, title = line.partition(" ")
        if BUILD_IN_TITLE.search(title):
            problems.append(f"{sha}: \"{title}\" has (Build N) in the title; the build-N tag carries the number (R-9)")
    return problems


def main() -> int:
    files = tracked_files()
    sections = [
        ("tracked files that must stay local", check_forbidden_files(files)),
        ("secrets", check_secrets(files)),
        ("commit titles", check_commit_titles()),
    ]
    banned, configured = check_banned_terms(files)
    sections.append(("banned names (BANNED_TERMS)", banned))

    failed = False
    for name, problems in sections:
        status = "FAIL" if problems else "ok"
        print(f"[{status:4}] {name}")
        for p in problems:
            print(f"        {p}")
        failed = failed or bool(problems)
    if not configured:
        print("[skip] banned names: BANNED_TERMS is not set, so no name check ran")
    print(f"\n{len(files)} tracked files checked.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
