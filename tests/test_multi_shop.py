"""
Tests that the agent itself follows the shop of the call (DEC-034): the right conversation
manager, the right greeting, the right knowledge folder, and a safe fallback.

    python -m pytest tests/test_multi_shop.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import shops  # noqa: E402
from dukaan_dost import transport as tp  # noqa: E402


@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


@pytest.fixture
def two_shops(app, tmp_path, monkeypatch):
    for name, display, say in [("alpha", "Alpha Kirana", "alpha-fallback"), ("beta", "Beta Store", "beta-fallback")]:
        folder = tmp_path / name
        (folder / "knowledge" / "core").mkdir(parents=True)
        (folder / "config.yaml").write_text(
            f'system_prompt: "prompt for {name}"\nfallback_messages:\n  en-in: "{say}"\ndisplay_name: "{display}"\n',
            encoding="utf-8")
        (folder / "knowledge" / "core" / "always_on.md").write_text(f"core of {name}", encoding="utf-8")
    monkeypatch.setattr(shops, "SHOPS_DIR", tmp_path)
    monkeypatch.setattr(app, "SHOP_NAME", "alpha")
    monkeypatch.setattr(app, "_conv_mgrs", {})
    monkeypatch.setattr(app, "_active_shop", "alpha")
    monkeypatch.delenv("SHOP_DISPLAY_NAME", raising=False)

    class FakeTransport(tp.Transport):
        shop = None
        def call_shop(self):
            return self.shop
    t = FakeTransport()
    monkeypatch.setattr(app, "_transport", t)
    return t


def test_a_call_for_a_shop_uses_that_shops_manager(app, two_shops):
    two_shops.shop = "beta"
    app._set_active_shop()
    assert app._active_shop == "beta"
    mgr = app._get_conv_mgr()
    assert mgr.shop_dir.name == "beta" and mgr._fallback_for("en-in") == "beta-fallback"


def test_each_shop_gets_its_own_manager_and_it_is_built_once(app, two_shops):
    a, b = app._get_conv_mgr("alpha"), app._get_conv_mgr("beta")
    assert a is not b and a.shop_dir.name == "alpha" and b.shop_dir.name == "beta"
    assert app._get_conv_mgr("alpha") is a and len(app._conv_mgrs) == 2


def test_the_greeting_names_the_shop_of_the_call(app, two_shops):
    two_shops.shop = "beta"
    app._set_active_shop()
    assert "Beta Store" in app._greeting()
    two_shops.shop = "alpha"
    app._set_active_shop()
    assert "Alpha Kirana" in app._greeting() and "Beta Store" not in app._greeting()


def test_an_unknown_shop_falls_back_to_the_default(app, two_shops):
    two_shops.shop = "ghost"
    app._set_active_shop()
    assert app._active_shop == "alpha"


def test_a_call_with_no_shop_uses_the_default(app, two_shops):
    two_shops.shop = None
    app._set_active_shop()
    assert app._active_shop == "alpha"


def test_knowledge_prefetch_reads_the_calls_shop(app, two_shops, monkeypatch):
    seen = {}

    def fake_prefetch(shop_dir, partial):
        seen["dir"] = shop_dir.name
    monkeypatch.setattr(app, "_prefetch_rag", fake_prefetch)

    class Session:
        latest_partial = "ek kilo chawal chahiye"
    two_shops.shop = "beta"
    app._set_active_shop()
    app._maybe_prefetch_rag(Session(), "")
    import time
    for _ in range(50):
        if "dir" in seen:
            break
        time.sleep(0.02)
    assert seen["dir"] == "beta"


def test_the_display_name_override_applies_to_the_default_shop_only(app, two_shops, monkeypatch):
    monkeypatch.setenv("SHOP_DISPLAY_NAME", "Custom Name")
    app._set_active_shop()                                    # alpha is the default
    assert "Custom Name" in app._greeting()
    two_shops.shop = "beta"
    app._set_active_shop()
    assert "Beta Store" in app._greeting() and "Custom Name" not in app._greeting()
