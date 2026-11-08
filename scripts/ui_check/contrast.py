#!/usr/bin/env python3
"""
ui_check/contrast.py: measure the contrast of every text-on-surface pair the pages use, in every theme, against WCAG 2.

    python scripts/ui_check/contrast.py            # print the table; exit 1 if any pair fails its threshold
    python scripts/ui_check/contrast.py --markdown # the same as a Markdown table, to paste in a doc

It reads the colour tokens straight from the page components (shared/tokens.css, which all three pages use), so the numbers
are those of the code, not of a copy. Themes measured: light and dark.

Thresholds (WCAG 2.2): 4.5:1 for text, 3:1 for the parts of an interface that must be seen (a filled button's edge,
an icon on its tile, a focus ring). A pair is listed with what it is used for, so a failure says what to fix.
The pages use solid colours only, so every pair here is exact. (If a translucent colour is ever added it needs a screenshot, not arithmetic.)
"""

import re
import sys
from pathlib import Path

COMPONENTS = Path(__file__).resolve().parent.parent.parent / "dukaan_dost" / "web" / "components"

TEXT, UI = 4.5, 3.0

# (foreground, background, minimum, what it is for). Names are token names without the leading dashes.
PAIRS = [
    ("ink", "bg", TEXT, "body text on the page"),
    ("ink", "surface", TEXT, "body text on a card"),
    ("ink", "surface2", TEXT, "text in a chip, a caller's bubble, a field"),
    ("muted", "bg", TEXT, "captions on the page"),
    ("muted", "surface", TEXT, "captions, labels and hints on a card"),
    ("muted", "surface2", TEXT, "captions inside a chip or bubble"),
    ("green-ink", "surface", TEXT, "links and the active tab on a card"),
    ("green-ink", "green-soft", TEXT, "the Ready pill, an agent's bubble, an active menu item"),
    ("blue", "blue-soft", TEXT, "the Thinking pill and the instalment figure"),
    ("blue", "surface", TEXT, "the hero figure's colour on a card"),
    ("credit", "credit-soft", TEXT, "the On credit pill"),
    ("amber", "amber-soft", TEXT, "the Needs attention and Credit pending pills, the demo-data banner"),
    ("amber", "surface", TEXT, "a warning heading on a card"),
    ("warn", "warn-soft", TEXT, "the Broken and Incomplete pills, an error banner"),
    ("warn", "surface", TEXT, "an error message under a form"),
    ("on-green", "green", TEXT, "the label on the green Start call and primary buttons"),
    ("on-end", "end", TEXT, "the hang-up icon on the red button"),
    ("green", "surface", UI, "the call ring, a switch that is on, the active tab's underline"),
    ("green", "bg", UI, "the same on the page itself"),
    ("blue", "blue-soft", UI, "an icon on the blue tile"),
    ("end", "surface", UI, "the red hang-up button against its card"),
    ("amber", "surface", UI, "the focus ring against a card"),
    # DEC-051: solid status tabs, a note slip, and the margin notes
    ("on-ink", "green", TEXT, "a Confirmed, Ordered or Ready status tab; the dashboard's live-call tab"),
    ("on-ink", "amber", TEXT, "a Credit pending or Needs attention tab; an amount in the attention list"),
    ("on-ink", "warn", TEXT, "an Incomplete or Broken tab; a problem notice's label"),
    ("on-ink", "credit", TEXT, "a Loan guidance tab"),
    ("on-ink", "muted", TEXT, "a No order tab"),
    ("bg", "ink", TEXT, "a count in the side menu"),
    ("paper-ink", "paper", TEXT, "the text of a note slip"),
    ("amber", "paper", TEXT, "a note slip's NOTE label"),
    ("warn", "surface", TEXT, "an italic margin note when the agent could not answer"),
]


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens_in(block: str) -> dict:
    return {m.group(1): m.group(2) for m in re.finditer(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})\b", block)}


def block(css: str, selector: str) -> str:
    """The text inside {...} of the rule whose selector is exactly `selector` (so ':root' does not match ':root[...]')."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if m is None:
        raise ValueError(f"no rule {selector!r} found")
    return m.group(1)


def themes() -> dict:
    base = (COMPONENTS / "shared" / "tokens.css").read_text(encoding="utf-8")
    light = tokens_in(block(base, ":root"))
    dark = tokens_in(block(base, ':root[data-theme="dark"]'))
    return {"light": light, "dark": dark}


def measure() -> list:
    rows = []
    for theme, tok in themes().items():
        for fg, bg, minimum, use in PAIRS:
            if fg not in tok or bg not in tok:
                rows.append((theme, fg, bg, None, minimum, use))
                continue
            rows.append((theme, fg, bg, ratio(tok[fg], tok[bg]), minimum, use))
    return rows


def main(argv) -> int:
    rows = measure()
    failing = [r for r in rows if r[3] is None or r[3] < r[4]]
    if "--markdown" in argv:
        print("| Theme | Text or part | On | Ratio | Needs | Used for |\n|---|---|---|---|---|---|")
        for theme, fg, bg, got, need, use in rows:
            mark = "" if got is not None and got >= need else " **FAILS**"
            print(f"| {theme} | `{fg}` | `{bg}` | {'?' if got is None else format(got, '.2f')}:1{mark} | {need}:1 | {use} |")
    else:
        for theme, fg, bg, got, need, use in rows:
            status = "ok  " if got is not None and got >= need else "FAIL"
            print(f"{status} {theme:<10} {fg:<10} on {bg:<11} {'  ?  ' if got is None else format(got, '5.2f')} (needs {need})  {use}")
        print(f"\n{len(rows) - len(failing)} of {len(rows)} pairs pass." + ("" if not failing else f" {len(failing)} FAIL."))
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
