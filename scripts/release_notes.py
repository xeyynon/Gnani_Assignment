#!/usr/bin/env python3
"""
Prints GitHub Release notes for a build tag, taken from its report.

    python scripts/release_notes.py build-1002

Uses the hand-written part of MD/builds/build-N.md (what changed, why, how it was
verified, what to improve next) and drops the generated "Files changed" list.
The "how it was verified" section is kept on purpose: it says what was NOT tested.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- Everything below is rebuilt from git"


def notes_for(tag: str) -> str:
    m = re.fullmatch(r"build-(\d+)", tag)
    if not m:
        raise SystemExit(f"{tag!r} is not a build tag (expected build-N)")
    report = ROOT / "MD" / "builds" / f"build-{m.group(1)}.md"
    if not report.exists():
        raise SystemExit(f"No build report at {report.relative_to(ROOT).as_posix()}")
    text = report.read_text(encoding="utf-8").replace("\r\n", "\n")
    text = text.split(MARKER)[0].strip()
    text = re.sub(r"^# Build \d+: .*\n+", "", text)            # the release already has a title
    text = re.sub(r"^\*\*Date:\*\* .*\n+", "", text, flags=re.M)
    text = re.sub(r"^## ", "### ", text, flags=re.M)
    return (text.strip() + f"\n\n---\nFull report: `MD/builds/build-{m.group(1)}.md`\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: release_notes.py build-N")
    sys.stdout.write(notes_for(sys.argv[1]))
