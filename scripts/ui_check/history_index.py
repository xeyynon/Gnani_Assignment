#!/usr/bin/env python3
"""
ui_check/history_index.py: build snapshots/CHANGES.md, the release-by-release record of how the pages looked and what changed.

    python scripts/ui_check/history_index.py

Reads, for every folder in snapshots/history/:
    release.json   written by snapshot_release.py: the release, its commit and date, which pages were captured
    manifest.json  every picture taken, and whether it scrolled sideways
and snapshots/history/changes.json, written by hand: for each folder, a title, a plain sentence on what changed on screen, the list of
visible changes, and anything not looked at. A release with no entry there is listed with a warning, so no release goes unexplained.

The page is a timeline, then one section per release with the previous release's picture beside this one (light and dark,
phone and desktop), so what changed can be seen without opening anything. Newest section last; `latest/INDEX.md` is the full current set.
"""

import json
import sys
from pathlib import Path

SNAPSHOTS = Path(__file__).resolve().parent.parent.parent / "snapshots"
HISTORY = SNAPSHOTS / "history"
PAGE_TITLES = {"call-page": "Call page", "dashboard": "Shop dashboard", "admin": "Admin page",
               "sign-in-shop": "Shop sign-in", "sign-in-admin": "Admin sign-in"}
SHOTS = [("phone", 390, 150), ("desktop", 1280, 300)]          # device, width, width of the thumbnail in the page


def img(label: str, page: str, theme: str, device: str, width: int, thumb: int) -> str:
    rel = f"history/{label}/{page}/01-landing/{theme}-{device}-{width}.png"
    if not (SNAPSHOTS / rel).exists():
        return "-"
    return f'<a href="{rel}"><img src="{rel}" width="{thumb}" alt="{PAGE_TITLES.get(page, page)}, {theme}, {device}"></a>'


def releases() -> list:
    out = []
    for folder in sorted(p for p in HISTORY.iterdir() if p.is_dir()):
        info = json.loads((folder / "release.json").read_text(encoding="utf-8")) if (folder / "release.json").exists() else {"label": folder.name, "pages": []}
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8")) if (folder / "manifest.json").exists() else []
        info["sideways"] = sorted({m["page"] for m in manifest if m.get("overflow")})
        out.append(info)
    return out


def main() -> int:
    notes = json.loads((HISTORY / "changes.json").read_text(encoding="utf-8")) if (HISTORY / "changes.json").exists() else {}
    rels = releases()
    missing = [r["label"] for r in rels if r["label"] not in notes]
    L = ["# What changed in the UI, release by release", "",
         "Each release's pages as they really looked then, taken from git by `scripts/ui_check/snapshot_release.py` (that release's own code and its own made-up data). "
         "Under each release the previous picture sits beside this one, in light and dark, on a phone and on a desktop, so a change can be seen without opening anything. "
         "Click a picture for the full-size page. The full set of every page and state today is in [latest/INDEX.md](latest/INDEX.md).", "",
         "Releases with no screen change (a build that only changed the agent, the evaluation or the docs) are not listed; the build reports in `MD/builds/` cover them.", "",
         "## Timeline", "", "| # | Release | Date | What changed on screen |", "|---|---|---|---|"]
    for r in rels:
        n = notes.get(r["label"], {})
        L.append(f"| {r['label'].split('-')[0]} | [{r['label'].split('-', 1)[1].replace('-', ' ')}](#{r['label']}) | {r.get('date', '')} | {n.get('summary', '(not described yet)')} |")
    L.append("")
    prev = None
    for r in rels:
        label, n = r["label"], notes.get(r["label"], {})
        L += [f'<a id="{label}"></a>', f"## {label.split('-')[0]}. {n.get('title') or r.get('title') or label}", ""]
        meta = f"Release `{r.get('rev', '')}`" + (f", commit `{r['commit']}`" if r.get("commit") and r.get("rev") != "working tree" else "") + (f", {r['date']}" if r.get("date") else "")
        if r.get("rev") == "working tree":
            meta = "The working tree: written, tested and looked at, **not committed yet**. When it is committed, retake it under its build number (see below)."
        if r.get("ran_code_of") not in (None, r.get("rev"), "the working tree"):
            meta += f". Run from `{r['ran_code_of']}`, the next commit, which has the same pages and a preview to run."
        L += [meta + ". Build report: " + (f"[`MD/builds/{r['rev']}.md`](../MD/builds/{r['rev']}.md)" if str(r.get("rev", "")).startswith("build-") else "none (not a build yet)") + ".", ""]
        if n.get("summary"):
            L += [f"**On screen:** {n['summary']}", ""]
        if n.get("visible"):
            L += ["What is different from the one before:", ""] + [f"- {v}" for v in n["visible"]] + [""]
        if n.get("not_looked_at"):
            L += [f"_Not looked at: {n['not_looked_at']}_", ""]
        if r["sideways"]:
            L += [f"**Scrolled sideways** on a phone or desktop in this release: {', '.join(PAGE_TITLES.get(p, p) for p in r['sideways'])}.", ""]
        L += ["| Page | Shown | Light: before | Light: this release | Dark: before | Dark: this release |", "|---|---|---|---|---|---|"]
        for page in r["pages"]:
            for device, width, thumb in SHOTS:
                cells = []
                for theme in ("light", "dark"):
                    before = img(prev["label"], page, theme, device, width, thumb) if prev and page in prev["pages"] else ("-" if prev else "")
                    if prev and page not in prev["pages"]:
                        before = "(new page)"
                    if prev is None:
                        before = "(first release)"
                    cells += [before, img(label, page, theme, device, width, thumb)]
                L.append(f"| {PAGE_TITLES.get(page, page)} | {device} {width} px | " + " | ".join(cells) + " |")
        L.append("")
        prev = r
    L += ["## Adding the next release", "",
          "After a build that changes how a page looks:", "",
          "```",
          "python scripts/ui_check/snapshot_release.py build-1023 16-build-1023     # the new build, from git",
          "# add an entry for \"16-build-1023\" to snapshots/history/changes.json: title, summary, visible, not_looked_at",
          "python scripts/ui_check/history_index.py                                  # rebuild this page",
          "```", "",
          "For a change that is not committed yet, use `--working-tree` and a label like `16-next-<what>`; when it is committed, delete that folder and take the real build.",
          "Then retake `latest/` (see `scripts/ui_check/snapshots.mjs`) so the full current set matches.", ""]
    (SNAPSHOTS / "CHANGES.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote snapshots/CHANGES.md for {len(rels)} releases")
    if missing:
        print("WARNING: no entry in changes.json for: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
