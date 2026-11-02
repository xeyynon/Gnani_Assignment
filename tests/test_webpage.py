"""
Offline tests for the page composer (dukaan_dost/webpage.py) and for the component folder
the two real pages are built from.

    python -m pytest tests/test_webpage.py
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import webpage  # noqa: E402


@pytest.fixture
def comps(tmp_path):
    folder = tmp_path / "components"
    folder.mkdir()
    (folder / "a").mkdir()
    (folder / "a" / "one.html").write_text("<b>one</b>\n", encoding="utf-8")
    (folder / "two.css").write_text("two{}\n", encoding="utf-8")
    (folder / "nest.html").write_text("[{{include:a/one.html}}]\n", encoding="utf-8")
    (folder / "loop.html").write_text("{{include:loop.html}}", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    return folder


def test_an_include_is_replaced_by_the_component(comps):
    assert webpage.compose("x {{include:a/one.html}} y", comps) == "x <b>one</b> y"


def test_the_tokens_own_line_does_not_leave_blank_lines(comps):
    assert webpage.compose("<style>\n{{include:two.css}}\n</style>", comps) == "<style>\ntwo{}\n</style>"


def test_components_can_include_components(comps):
    assert webpage.compose("{{include:nest.html}}", comps) == "[<b>one</b>]"


def test_the_shop_placeholder_is_left_for_the_caller(comps):
    assert webpage.compose("<h1>{{SHOP}}</h1>{{include:two.css}}", comps) == "<h1>{{SHOP}}</h1>two{}"


def test_a_missing_component_is_an_error_not_a_gap(comps):
    with pytest.raises(webpage.ComponentError, match="does not exist"):
        webpage.compose("{{include:nope.html}}", comps)


@pytest.mark.parametrize("name", ["../secret.txt", "a/../../secret.txt", "../components/../secret.txt"])
def test_nothing_outside_the_folder_can_be_read(comps, name):
    with pytest.raises(webpage.ComponentError):
        webpage.compose("{{include:%s}}" % name, comps)


def test_an_absolute_path_cannot_be_included(comps):
    with pytest.raises(webpage.ComponentError):
        webpage.compose("{{include:/a/one.html}}", comps)


def test_a_component_that_includes_itself_stops(comps):
    with pytest.raises(webpage.ComponentError, match="nested too deeply"):
        webpage.compose("{{include:loop.html}}", comps)


def test_included_names_follow_nesting(comps):
    assert webpage.included_names("{{include:nest.html}} {{include:two.css}}", comps) == {"nest.html", "a/one.html", "two.css"}


# ---- the real pages and the real components -----------------------------------
def _pages():
    return {p.name: p for p in webpage.WEB.glob("*.html")}


def test_both_real_pages_compose_completely():
    assert set(_pages()) == {"index.html", "dashboard.html"}
    for name, path in _pages().items():
        text = webpage.load(path)
        assert "{{include:" not in text, f"{name} has an include that did not resolve"
        assert "{{SHOP}}" in text, f"{name} lost its shop-name placeholder"
        assert len(text) > 1000


def test_every_component_is_used_by_a_page():
    """An orphaned component is dead code: it looks like part of the interface and is not."""
    used = set()
    for path in _pages().values():
        used |= webpage.included_names(path.read_text(encoding="utf-8"))
    on_disk = {p.relative_to(webpage.COMPONENTS).as_posix() for p in webpage.COMPONENTS.rglob("*") if p.is_file()}
    assert on_disk - used == set(), f"components no page uses: {sorted(on_disk - used)}"
    assert used - on_disk == set()


def test_no_component_holds_a_script_or_style_tag_of_its_own():
    """Each component is one kind of thing (markup, styles or script). The page owns the tags around them."""
    for p in webpage.COMPONENTS.rglob("*"):
        if p.is_file() and p.suffix in (".css", ".js"):
            text = p.read_text(encoding="utf-8")
            assert "<script" not in text and "<style" not in text, f"{p.name} has a tag of its own"


def test_the_command_line_prints_a_page_and_rejects_nonsense():
    out = subprocess.run([sys.executable, "-m", "dukaan_dost.webpage", "index"], capture_output=True, cwd=ROOT)
    assert out.returncode == 0 and b"<!doctype html>" in out.stdout
    bad = subprocess.run([sys.executable, "-m", "dukaan_dost.webpage", "nonsense"], capture_output=True, cwd=ROOT)
    assert bad.returncode == 2
