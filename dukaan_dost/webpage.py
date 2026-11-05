"""
webpage.py

The two web pages (the call page and the shopkeeper dashboard) are built from
components: small files under web/components/, each one a single piece of the
interface (a colour token set, an icon sheet, the theme button, the order table,
the live transcript...). A page is a short template that lists the components it
is made of:

    {{include:shared/theme-button.html}}

and the server stitches them together each time it serves the page. The page still
arrives as ONE self-contained response, so nothing extra is fetched and the
dashboard's strict content security policy (which allows no outside files) is
unchanged.

Rules:
  - An include names a file inside web/components/ (letters, digits, _ - . /). Nothing
    outside that folder can be read.
  - Components may include other components, up to a small depth, which also stops a
    component that includes itself.
  - A missing component is an error, never a silent gap: a page with a hole in it is
    worse than a page that does not load.
  - {{SHOP}} is NOT filled in here; the caller does that, with the name escaped.

    python -m dukaan_dost.webpage index        # print the composed call page
    python -m dukaan_dost.webpage dashboard    # print the composed dashboard
    python -m dukaan_dost.webpage admin        # print the composed admin page
    python -m dukaan_dost.webpage login        # print the composed sign-in page (placeholders unfilled)
"""

import re
import sys
from pathlib import Path

WEB = Path(__file__).parent / "web"
COMPONENTS = WEB / "components"

INCLUDE = re.compile(r"\{\{include:([A-Za-z0-9_./-]+)\}\}")
MAX_DEPTH = 6


class ComponentError(Exception):
    """A page asked for a component that is missing, outside the folder, or nested too deeply."""


def _read(name: str, root: Path) -> str:
    base = root.resolve()
    path = (base / name).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise ComponentError(f"component {name!r} is outside the components folder") from None
    if not path.is_file():
        raise ComponentError(f"component {name!r} does not exist")
    return path.read_text(encoding="utf-8")


def compose(source: str, root: Path | None = None, _depth: int = 0) -> str:
    """Replace every {{include:name}} in `source` with that component's text (recursively)."""
    root = root or COMPONENTS
    if _depth > MAX_DEPTH:
        raise ComponentError("components are nested too deeply (does one include itself?)")
    return INCLUDE.sub(lambda m: compose(_read(m.group(1), root).rstrip("\n"), root, _depth + 1), source)


def load(page: Path, root: Path | None = None) -> str:
    """A page template, with its components stitched in."""
    return compose(page.read_text(encoding="utf-8"), root)


def included_names(source: str, root: Path | None = None, _depth: int = 0) -> set:
    """Every component name a template uses, directly or through other components."""
    root = root or COMPONENTS
    if _depth > MAX_DEPTH:
        raise ComponentError("components are nested too deeply (does one include itself?)")
    names = set()
    for name in INCLUDE.findall(source):
        names.add(name)
        names |= included_names(_read(name, root), root, _depth + 1)
    return names


def main(argv: list) -> int:
    page = {"index": "index.html", "dashboard": "dashboard.html", "admin": "admin.html", "login": "login.html"}.get(argv[0] if argv else "")
    if page is None:
        print("usage: python -m dukaan_dost.webpage index|dashboard|admin|login", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(load(WEB / page).encode("utf-8"))      # bytes, so a Windows console code page cannot break it
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
