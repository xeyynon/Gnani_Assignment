#!/usr/bin/env python3
"""
Checks that every relative link in the project's Markdown files points at a file
that exists. The docs were renamed and restructured a lot, and they link to each
other heavily, so a moved file would otherwise leave quiet dead links.

    python scripts/check_docs.py

Skips web links, mail links, in-page anchors, and anything inside code blocks or
inline code. The generated build reports in MD/builds/ are checked too.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FENCE = re.compile(r"^(```|~~~).*?^\1\s*$", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "data:")


def markdown_files():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / f for f in out.splitlines() if f]


def broken_links(md: Path):
    text = md.read_text(encoding="utf-8")
    text = FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    for m in LINK.finditer(text):
        target = m.group(1)
        if target.startswith(SKIP_PREFIXES):
            continue
        path_part = re.split(r"[#?]", target, 1)[0]
        if not path_part:
            continue
        base = ROOT if path_part.startswith("/") else md.parent
        resolved = (base / path_part.lstrip("/")).resolve()
        if not resolved.exists():
            line_no = text.count("\n", 0, m.start()) + 1
            yield line_no, target


def main() -> int:
    files = markdown_files()
    bad = 0
    for md in files:
        for line_no, target in broken_links(md):
            bad += 1
            print(f"{md.relative_to(ROOT).as_posix()}:{line_no}: broken link -> {target}")
    print(f"{len(files)} Markdown files checked, {bad} broken link(s).")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
