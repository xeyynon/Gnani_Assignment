"""
Tests for shop_health.py: what the admin dashboard says is wrong with a shop.

Each shop here is a small folder built in a temp directory; nothing reads the real shops/ or data/.

    python -m pytest tests/test_shop_health.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import auth, shop_health, store  # noqa: E402
from dukaan_dost.knowledge_retriever import CORE_FILENAME, KNOWLEDGE_FILES  # noqa: E402

CONFIG = 'system_prompt: "You help customers."\nfallback_messages:\n  en-in: "Sorry."\n'


def make_shop(root: Path, name: str = "alpha", config: str | None = CONFIG, core: bool = True,
              topics=None, stock="ok") -> Path:
    folder = root / name
    (folder / "knowledge" / "core").mkdir(parents=True)
    if config is not None:
        (folder / "config.yaml").write_text(config, encoding="utf-8")
    if core:
        (folder / "knowledge" / CORE_FILENAME).write_text("# Who we are\n", encoding="utf-8")
    for topic in (KNOWLEDGE_FILES if topics is None else topics):
        (folder / "knowledge" / topic).write_text("## x\ny\n", encoding="utf-8")
    if stock == "ok":
        (folder / "stock.json").write_text(json.dumps({"items": [{"sku": "A", "price": 1}]}), encoding="utf-8")
    elif stock == "bad":
        (folder / "stock.json").write_text("{not json", encoding="utf-8")
    elif stock == "empty":
        (folder / "stock.json").write_text(json.dumps({"items": []}), encoding="utf-8")
    return folder


@pytest.fixture
def env(tmp_path):
    shops_root, orders_root, auth_file = tmp_path / "shops", tmp_path / "orders", tmp_path / "auth.json"
    shops_root.mkdir()
    return shops_root, orders_root, auth_file


def check(env, name="alpha"):
    shops_root, orders_root, auth_file = env
    return shop_health.check(name, shops_root, orders_root, auth_file)


def codes(problems):
    return {p["id"].split(":", 1)[1] for p in problems}


def test_a_complete_shop_with_a_pin_has_no_problems(env):
    make_shop(env[0])
    auth.set_pin("alpha", "1111", env[2])
    assert check(env) == []


def test_a_shop_with_no_pin_is_a_warning_not_an_error(env):
    make_shop(env[0])
    found = check(env)
    assert codes(found) == {"no-pin"} and found[0]["severity"] == "warning"


@pytest.mark.parametrize("config", ["system_prompt: [unclosed", "- just\n- a list\n", ""])
def test_a_config_the_agent_cannot_load_is_an_error(env, config):
    make_shop(env[0], config=config)
    found = check(env)
    assert "config-unreadable" in codes(found)
    assert [p for p in found if p["id"].endswith("config-unreadable")][0]["severity"] == "error"


def test_a_missing_config_file_is_an_error(env):
    make_shop(env[0], config=None)
    assert "config-unreadable" in codes(check(env))


def test_no_system_prompt_is_an_error(env):
    make_shop(env[0], config='fallback_messages:\n  en-in: "Sorry."\n')
    assert "no-prompt" in codes(check(env))
    assert "no-prompt" in codes(check(env)) and "no-fallback" not in codes(check(env))


def test_a_blank_system_prompt_is_an_error(env):
    make_shop(env[0], config='system_prompt: "   "\nfallback_messages:\n  en-in: "x"\n')
    assert "no-prompt" in codes(check(env))


@pytest.mark.parametrize("fallbacks", ["", "fallback_messages: {}\n", 'fallback_messages:\n  hi-in: "x"\n'])
def test_no_english_fallback_is_an_error(env, fallbacks):
    make_shop(env[0], config='system_prompt: "x"\n' + fallbacks)
    assert "no-fallback" in codes(check(env))


def test_the_english_fallback_key_is_matched_in_any_case(env):
    make_shop(env[0], config='system_prompt: "x"\nfallback_messages:\n  EN-IN: "x"\n')
    assert "no-fallback" not in codes(check(env))


def test_missing_always_on_knowledge_is_an_error(env):
    make_shop(env[0], core=False)
    found = [p for p in check(env) if p["id"].endswith("no-always-on")]
    assert found and found[0]["severity"] == "error"


def test_each_missing_topic_file_is_its_own_warning(env):
    make_shop(env[0], topics=KNOWLEDGE_FILES[:5])
    missing = [p for p in check(env) if ":missing-" in p["id"]]
    assert {p["id"] for p in missing} == {f"alpha:missing-{n}" for n in KNOWLEDGE_FILES[5:]}
    assert all(p["severity"] == "warning" for p in missing)


@pytest.mark.parametrize("stock,expected,severity", [
    (None, "no-stock", "warning"), ("bad", "stock-unreadable", "error"), ("empty", "stock-empty", "warning")])
def test_stock_list_problems(env, stock, expected, severity):
    make_shop(env[0], stock=stock)
    found = [p for p in check(env) if p["id"].endswith(expected)]
    assert found and found[0]["severity"] == severity


def test_unreadable_order_files_are_one_warning_with_a_count(env):
    make_shop(env[0])
    folder = store.shop_orders_dir("alpha", env[1])
    folder.mkdir(parents=True)
    (folder / "order_a1.json").write_text("{broken", encoding="utf-8")
    (folder / "order_a2.json").write_text("also broken", encoding="utf-8")
    found = [p for p in check(env) if p["id"].endswith("unreadable-data")]
    assert len(found) == 1 and found[0]["title"].startswith("2 order or loan files")


def test_errors_come_before_warnings_and_ids_are_unique_and_stable(env):
    make_shop(env[0], config=None, core=False, topics=[], stock=None)
    found = check(env)
    severities = [p["severity"] for p in found]
    assert severities == sorted(severities, key=lambda s: shop_health.SEVERITY_ORDER[s])
    ids = [p["id"] for p in found]
    assert len(ids) == len(set(ids))
    assert ids == [p["id"] for p in check(env)]


def test_every_problem_has_the_fields_a_page_needs(env):
    make_shop(env[0], config=None, topics=[])
    for p in check(env):
        assert set(p) == {"id", "shop", "severity", "title", "detail"}
        assert p["shop"] == "alpha" and p["title"] and p["detail"]


@pytest.mark.parametrize("name", ["../etc", "A B", "", "x" * 60, "a/b"])
def test_an_invalid_shop_name_is_never_turned_into_a_path(env, name):
    assert shop_health.check(name, env[0], env[1], env[2]) == []
