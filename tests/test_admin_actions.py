"""
Tests for admin_actions.py: everything the admin dashboard can change.

Every test works in a temporary folder; nothing touches the real shops/ or data/. The point of most of them is what
must NOT happen: a half-made shop, an overwritten shop, a path out of the folder, an invalid stock list on disk, an
error hidden by marking it solved.

    python -m pytest tests/test_admin_actions.py
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import admin_actions as act, auth, shop_health, shops, stock  # noqa: E402
from dukaan_dost.conversation_manager import ConversationManager  # noqa: E402
from tests.test_shop_health import make_shop  # noqa: E402

ITEM = {"sku": "RICE-1KG", "category": "staples", "unit": "kg", "price": 60, "in_stock": True,
        "name": {"en": "Rice", "hi": "चावल", "te": "బియ్యం"}, "pack": "per kg", "aliases": ["rice", "chawal"]}


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "shops"
    root.mkdir()
    return root, tmp_path / "auth.json", tmp_path / "state.json", tmp_path / "orders"


def stocked_shop(root, name="alpha"):
    folder = make_shop(root, name, config='display_name: "Alpha"\nsystem_prompt: "Be kind."\nfallback_messages:\n  en-in: "Sorry."\n')
    (folder / "stock.json").write_text(json.dumps({"currency": "INR", "items": [dict(ITEM)]}), encoding="utf-8")
    return folder


# ---- create -------------------------------------------------------------------

def test_a_blank_shop_is_complete_enough_for_the_agent_to_load(env):
    root, auth_file, _, _ = env
    out = act.create_shop("new_shop", "New Shop", "blank", "4321", root, auth_file)
    assert out == {"name": "new_shop", "pin": "4321", "pin_generated": False}
    assert shops.exists("new_shop", root) and auth.check_pin("new_shop", "4321", auth_file)
    mgr = ConversationManager(shop_dir=shops.shop_dir("new_shop", root), llm_model="x", max_tokens=10, temperature=0)
    assert "voice assistant" in mgr.base_prompt and "en-in" in mgr.fallback_messages
    assert shops.display_name("new_shop", root) == "New Shop"


def test_a_blank_shop_asks_for_its_stock_but_has_no_errors(env):
    root, auth_file, _, orders = env
    act.create_shop("new_shop", "New Shop", pin="4321", shops_root=root, auth_path=auth_file)
    found = shop_health.check("new_shop", root, orders, auth_file)
    assert [p["id"] for p in found] == ["new_shop:stock-empty"] and found[0]["severity"] == "warning"


def test_a_generated_pin_is_returned_once_and_works(env):
    root, auth_file, _, _ = env
    out = act.create_shop("shop_two", "Shop Two", shops_root=root, auth_path=auth_file)
    assert out["pin_generated"] and len(out["pin"]) == act.GENERATED_PIN_DIGITS and out["pin"].isdigit()
    assert auth.check_pin("shop_two", out["pin"], auth_file)
    stored = json.loads(auth_file.read_text(encoding="utf-8"))
    values = [str(v) for entry in stored.values() for v in (entry.values() if isinstance(entry, dict) else [entry])]
    assert out["pin"] not in values                                            # stored hashed, never in clear
    # (not a substring test: a short run of digits turns up by chance inside a hex hash and made this test flaky)


def test_a_new_shop_can_be_a_copy_of_an_existing_one_with_its_own_name(env):
    root, auth_file, _, _ = env
    stocked_shop(root, "alpha")
    act.create_shop("beta", "Beta Store", "alpha", "9999", root, auth_file)
    beta = shops.shop_dir("beta", root)
    assert shops.display_name("beta", root) == "Beta Store" and shops.display_name("alpha", root) == "Alpha"
    assert json.loads((beta / "stock.json").read_text(encoding="utf-8"))["items"][0]["sku"] == "RICE-1KG"
    assert (beta / "knowledge" / "core" / "always_on.md").is_file()
    assert not list(beta.rglob("*.bak")) and not list(beta.rglob("*.tmp"))
    assert not auth.has_pin("alpha", auth_file) and auth.check_pin("beta", "9999", auth_file)   # the copy does not share a PIN


def test_an_existing_shop_is_never_overwritten(env):
    root, auth_file, _, _ = env
    stocked_shop(root, "alpha")
    before = (shops.shop_dir("alpha", root) / "config.yaml").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        act.create_shop("alpha", "Other", "blank", "1234", root, auth_file)
    assert (shops.shop_dir("alpha", root) / "config.yaml").read_text(encoding="utf-8") == before


def test_a_folder_with_no_config_also_blocks_the_name(env):
    root, auth_file, _, _ = env
    (root / "ghost").mkdir()
    with pytest.raises(ValueError, match="already exists"):
        act.create_shop("ghost", "Ghost", "blank", "1234", root, auth_file)


@pytest.mark.parametrize("name", ["../evil", "A B", "", "x", "a/b", "x" * 41, ".hidden", "Upper", None, 7])
def test_a_bad_shop_name_is_refused_before_anything_is_written(env, name):
    root, auth_file, _, _ = env
    with pytest.raises(ValueError):
        act.create_shop(name, "Name", "blank", "1234", root, auth_file)
    assert list(root.iterdir()) == [] and not auth_file.exists()


@pytest.mark.parametrize("title", ["", "   ", None, "x" * 61, 5])
def test_the_display_name_is_required_and_bounded(env, title):
    root, auth_file, _, _ = env
    with pytest.raises(ValueError):
        act.create_shop("shop_x", title, "blank", "1234", root, auth_file)
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("pin", ["123", "ab", 1234, ["1234"]])
def test_a_weak_or_odd_pin_is_refused_and_nothing_is_created(env, pin):
    root, auth_file, _, _ = env
    with pytest.raises(ValueError, match="PIN"):
        act.create_shop("shop_x", "X Shop", "blank", pin, root, auth_file)
    assert list(root.iterdir()) == [] and not auth_file.exists()


@pytest.mark.parametrize("template", ["nope", "../alpha", "A B"])
def test_a_missing_or_odd_template_is_refused(env, template):
    root, auth_file, _, _ = env
    stocked_shop(root, "alpha")
    with pytest.raises(ValueError, match="copy from"):
        act.create_shop("shop_x", "X Shop", template, "1234", root, auth_file)
    assert shops.list_folders(root) == ["alpha"]


def test_a_failure_part_way_leaves_no_hidden_folder_behind(env, monkeypatch):
    root, auth_file, _, _ = env

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(act, "_write_blank", boom)
    with pytest.raises(OSError):
        act.create_shop("shop_x", "X Shop", "blank", "1234", root, auth_file)
    assert list(root.iterdir()) == []


def test_the_hidden_build_folder_is_never_listed_as_a_shop(env):
    root, _, _, _ = env
    (root / ".new-half").mkdir()
    assert shops.list_folders(root) == [] and shops.list_shops(root) == []


# ---- pin ----------------------------------------------------------------------

def test_a_pin_can_be_reset_to_a_chosen_or_generated_one(env):
    root, auth_file, _, _ = env
    stocked_shop(root)
    auth.set_pin("alpha", "1111", auth_file)
    assert act.set_pin("alpha", "2222", root, auth_file)["pin_generated"] is False
    assert auth.check_pin("alpha", "2222", auth_file) and not auth.check_pin("alpha", "1111", auth_file)
    out = act.set_pin("alpha", None, root, auth_file)
    assert out["pin_generated"] and auth.check_pin("alpha", out["pin"], auth_file)


@pytest.mark.parametrize("shop", ["nope", "../x", "", None])
def test_a_pin_for_a_missing_shop_is_refused(env, shop):
    root, auth_file, _, _ = env
    with pytest.raises(ValueError):
        act.set_pin(shop, "1234", root, auth_file)
    assert not auth_file.exists()


# ---- prompt -------------------------------------------------------------------

def test_the_editor_reads_name_prompt_and_stock(env):
    root, *_ = env
    stocked_shop(root)
    got = act.get_shop("alpha", root)
    assert got["display_name"] == "Alpha" and got["system_prompt"].startswith("Be kind")
    assert got["stock"] == [{"sku": "RICE-1KG", "name": "Rice", "unit": "kg", "price": 60, "in_stock": True}]


def test_saving_the_prompt_keeps_a_copy_of_the_old_file_and_the_other_settings(env):
    root, *_ = env
    folder = stocked_shop(root)
    (folder / "config.yaml").write_text('display_name: "Alpha"\nsystem_prompt: "Old."\nfallback_messages:\n  en-in: "Sorry."\norder_closing:\n  en-in: "Thanks."\n', encoding="utf-8")
    act.save_prompt("alpha", "New instructions.\n\nसाफ़ रहें।", "Alpha Two", root)
    config = yaml.safe_load((folder / "config.yaml").read_text(encoding="utf-8"))
    assert config["system_prompt"].strip() == "New instructions.\n\nसाफ़ रहें।" and config["display_name"] == "Alpha Two"
    assert config["order_closing"] == {"en-in": "Thanks."} and config["fallback_messages"] == {"en-in": "Sorry."}
    assert "Old." in (folder / "config.yaml.bak").read_text(encoding="utf-8")
    assert shops.display_name("alpha", root) == "Alpha Two"


@pytest.mark.parametrize("prompt", ["", "   \n", None, 5, "x" * (act.MAX_PROMPT_CHARS + 1)])
def test_an_unusable_prompt_is_refused_and_the_file_is_untouched(env, prompt):
    root, *_ = env
    folder = stocked_shop(root)
    before = (folder / "config.yaml").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        act.save_prompt("alpha", prompt, "Alpha", root)
    assert (folder / "config.yaml").read_text(encoding="utf-8") == before and not (folder / "config.yaml.bak").exists()


def test_a_config_that_cannot_be_read_is_not_overwritten(env):
    root, *_ = env
    folder = make_shop(root, "alpha", config="system_prompt: [unclosed")
    with pytest.raises(ValueError, match="cannot be read"):
        act.save_prompt("alpha", "New.", "Alpha", root)
    with pytest.raises(ValueError, match="cannot be read"):
        act.get_shop("alpha", root)
    assert (folder / "config.yaml").read_text(encoding="utf-8") == "system_prompt: [unclosed"


# ---- stock --------------------------------------------------------------------

def stock_of(folder):
    return json.loads((folder / "stock.json").read_text(encoding="utf-8"))["items"]


def test_prices_and_availability_change_and_the_knowledge_file_follows(env):
    root, *_ = env
    folder = stocked_shop(root)
    act.save_stock("alpha", update=[{"sku": "RICE-1KG", "price": 72.5, "in_stock": False}], shops_root=root)
    item = stock_of(folder)[0]
    assert item["price"] == 72.5 and item["in_stock"] is False
    assert (folder / "knowledge" / "products_pricing.md").read_text(encoding="utf-8") == stock.render_products_md(stock_of(folder))


def test_an_item_can_be_added_and_removed(env):
    root, *_ = env
    folder = stocked_shop(root)
    new = dict(ITEM, sku="SUGAR-1KG", name={"en": "Sugar", "hi": "चीनी", "te": "చక్కెర"}, aliases=["sugar"], price=44)
    act.save_stock("alpha", add=[new], shops_root=root)
    assert [i["sku"] for i in stock_of(folder)] == ["RICE-1KG", "SUGAR-1KG"]
    act.save_stock("alpha", remove=["RICE-1KG"], shops_root=root)
    assert [i["sku"] for i in stock_of(folder)] == ["SUGAR-1KG"]


def test_other_keys_in_stock_json_survive_an_edit(env):
    root, *_ = env
    folder = stocked_shop(root)
    data = json.loads((folder / "stock.json").read_text(encoding="utf-8"))
    data["_note"] = "keep me"
    (folder / "stock.json").write_text(json.dumps(data), encoding="utf-8")
    act.save_stock("alpha", update=[{"sku": "RICE-1KG", "price": 61}], shops_root=root)
    assert json.loads((folder / "stock.json").read_text(encoding="utf-8"))["_note"] == "keep me"


@pytest.mark.parametrize("change", [
    {"sku": "RICE-1KG", "price": 0}, {"sku": "RICE-1KG", "price": -5}, {"sku": "RICE-1KG", "price": "60"},
    {"sku": "RICE-1KG", "price": True}, {"sku": "RICE-1KG", "in_stock": "yes"}, {"sku": "NOPE", "price": 5}])
def test_a_bad_stock_change_is_refused_and_nothing_is_written(env, change):
    root, *_ = env
    folder = stocked_shop(root)
    before = (folder / "stock.json").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        act.save_stock("alpha", update=[change], shops_root=root)
    assert (folder / "stock.json").read_text(encoding="utf-8") == before


def test_one_bad_change_in_a_batch_applies_none_of_it(env):
    root, *_ = env
    folder = stocked_shop(root)
    before = (folder / "stock.json").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        act.save_stock("alpha", update=[{"sku": "RICE-1KG", "price": 99}, {"sku": "NOPE", "price": 5}], shops_root=root)
    assert (folder / "stock.json").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("bad", [
    dict(ITEM, sku="lower-case"), dict(ITEM, unit="tonne"), dict(ITEM, aliases=[]), dict(ITEM, name={"en": "Rice"}),
    dict(ITEM, in_stock="yes"), dict(ITEM, price=0)])
def test_an_item_that_would_make_the_list_invalid_is_not_added(env, bad):
    root, *_ = env
    folder = stocked_shop(root)
    before = (folder / "stock.json").read_text(encoding="utf-8")
    bad = dict(bad, sku=bad["sku"] if bad["sku"] != "RICE-1KG" else "OTHER-1")
    with pytest.raises(ValueError, match="not be valid"):
        act.save_stock("alpha", add=[bad], shops_root=root)
    assert (folder / "stock.json").read_text(encoding="utf-8") == before


def test_adding_an_item_that_exists_or_removing_one_that_does_not_is_refused(env):
    root, *_ = env
    stocked_shop(root)
    with pytest.raises(ValueError, match="already"):
        act.save_stock("alpha", add=[dict(ITEM)], shops_root=root)
    with pytest.raises(ValueError, match="no item"):
        act.save_stock("alpha", remove=["NOPE"], shops_root=root)


def test_an_unreadable_stock_file_is_not_overwritten(env):
    root, *_ = env
    folder = make_shop(root, "alpha", stock="bad")
    with pytest.raises(ValueError, match="cannot be read"):
        act.save_stock("alpha", update=[{"sku": "A", "price": 1}], shops_root=root)
    assert (folder / "stock.json").read_text(encoding="utf-8") == "{not json"


# ---- solved problems ----------------------------------------------------------

def test_a_warning_can_be_marked_solved_and_brought_back(env):
    root, auth_file, state, orders = env
    make_shop(root, "gamma")                                              # fine, but no PIN: a warning
    act.dismiss("gamma:no-pin", "set up next week", root, orders, auth_file, state)
    got = act.dismissed(state)
    assert list(got) == ["gamma:no-pin"] and got["gamma:no-pin"]["note"] == "set up next week" and got["gamma:no-pin"]["at"]
    act.restore("gamma:no-pin", state)
    assert act.dismissed(state) == {}


def test_an_error_cannot_be_marked_solved(env):
    root, auth_file, state, orders = env
    make_shop(root, "beta", config=None)
    with pytest.raises(ValueError, match="cannot be marked solved"):
        act.dismiss("beta:config-unreadable", "", root, orders, auth_file, state)
    assert act.dismissed(state) == {}


@pytest.mark.parametrize("pid", ["gamma:nothing", "nocolon", "../x:no-pin", "", None, 5, "nope:no-pin"])
def test_an_unknown_problem_cannot_be_marked_solved(env, pid):
    root, auth_file, state, orders = env
    make_shop(root, "gamma")
    with pytest.raises(ValueError):
        act.dismiss(pid, "", root, orders, auth_file, state)
    assert not state.exists()


def test_restoring_something_never_dismissed_is_refused(env):
    with pytest.raises(ValueError, match="not marked solved"):
        act.restore("gamma:no-pin", env[2])


def test_a_damaged_state_file_reads_as_nothing_dismissed_and_is_replaced_on_the_next_write(env):
    root, auth_file, state, orders = env
    make_shop(root, "gamma")
    state.write_text("{broken", encoding="utf-8")
    assert act.dismissed(state) == {}
    act.dismiss("gamma:no-pin", "", root, orders, auth_file, state)
    assert list(act.dismissed(state)) == ["gamma:no-pin"]


def test_a_note_is_cut_to_a_sane_length(env):
    root, auth_file, state, orders = env
    make_shop(root, "gamma")
    act.dismiss("gamma:no-pin", "n" * 5000, root, orders, auth_file, state)
    assert len(act.dismissed(state)["gamma:no-pin"]["note"]) == 200
