"""
Offline tests for the shop registry, sign-in, order store and demo data (DEC-034).

    python -m pytest tests/test_shops_auth_store.py
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import auth, demo_data, shops, store  # noqa: E402
from dukaan_dost.loan_calculator import quote  # noqa: E402

NOW = datetime(2026, 11, 2, 15, 30, tzinfo=store.IST)


# ---- shops -----------------------------------------------------------------

@pytest.mark.parametrize("name", ["dukaan_dost", "ab", "shop-2", "a" * 40, "0shop"])
def test_good_shop_names(name):
    assert shops.valid_name(name)


@pytest.mark.parametrize("name", [
    "", "a", "A", "Shop", "../etc", "..", "a/b", "a\\b", "a b", "-shop", "_shop", "a" * 41,
    "shop.json", "shop%2f", None, 5, "shöp",
])
def test_bad_shop_names_never_reach_the_disk(name, tmp_path):
    assert not shops.valid_name(name)
    assert not shops.exists(name, tmp_path)
    if isinstance(name, str):
        with pytest.raises(ValueError):
            shops.shop_dir(name, tmp_path)


def make_shop(root, name, display=None):
    folder = root / name
    folder.mkdir(parents=True)
    config = 'system_prompt: "hi"\nfallback_messages:\n  en-in: "sorry"\n'
    if display:
        config += f'display_name: "{display}"\n'
    (folder / "config.yaml").write_text(config, encoding="utf-8")
    return folder


def test_list_and_exists_only_count_folders_with_a_config(tmp_path):
    make_shop(tmp_path, "alpha")
    make_shop(tmp_path, "beta")
    (tmp_path / "gamma").mkdir()                       # no config.yaml
    (tmp_path / "Bad Name").mkdir()
    (tmp_path / "README.md").write_text("x")
    assert shops.list_shops(tmp_path) == ["alpha", "beta"]
    assert shops.exists("alpha", tmp_path) and not shops.exists("gamma", tmp_path)
    assert shops.list_shops(tmp_path / "missing") == []


def test_display_name_from_config_or_folder(tmp_path):
    make_shop(tmp_path, "ram_kirana", display="Ram Kirana Store")
    make_shop(tmp_path, "sai-general")
    assert shops.display_name("ram_kirana", tmp_path) == "Ram Kirana Store"
    assert shops.display_name("sai-general", tmp_path) == "Sai General"
    assert shops.display_name("unknown", tmp_path) == "Unknown"


# ---- auth ------------------------------------------------------------------

@pytest.fixture
def auth_file(tmp_path):
    return tmp_path / "data" / "auth.json"


def test_a_pin_works_and_a_wrong_one_does_not(auth_file):
    auth.set_pin("alpha", "4821", auth_file)
    assert auth.check_pin("alpha", "4821", auth_file)
    assert not auth.check_pin("alpha", "4822", auth_file)
    assert not auth.check_pin("alpha", "", auth_file)
    assert not auth.check_pin("alpha", None, auth_file)


def test_the_pin_is_not_stored_in_the_clear(auth_file):
    auth.set_pin("alpha", "4821", auth_file)
    assert "4821" not in auth_file.read_text(encoding="utf-8")


def test_a_shop_with_no_pin_cannot_sign_in(auth_file):
    assert not auth.check_pin("alpha", "", auth_file)
    assert not auth.check_pin("alpha", "0000", auth_file)
    assert not auth.has_pin("alpha", auth_file)


def test_one_shops_pin_does_not_open_another(auth_file):
    auth.set_pin("alpha", "1111", auth_file)
    auth.set_pin("beta", "2222", auth_file)
    assert auth.check_pin("alpha", "1111", auth_file) and not auth.check_pin("alpha", "2222", auth_file)
    assert auth.check_pin("beta", "2222", auth_file) and not auth.check_pin("beta", "1111", auth_file)


def test_changing_a_pin_replaces_the_old_one(auth_file):
    auth.set_pin("alpha", "1111", auth_file)
    auth.set_pin("alpha", "9999", auth_file)
    assert auth.check_pin("alpha", "9999", auth_file) and not auth.check_pin("alpha", "1111", auth_file)


def test_the_same_pin_is_hashed_differently_each_time(auth_file):
    auth.set_pin("alpha", "1111", auth_file)
    first = json.loads(auth_file.read_text())["shops"]["alpha"]["hash"]
    auth.set_pin("alpha", "1111", auth_file)
    assert json.loads(auth_file.read_text())["shops"]["alpha"]["hash"] != first


@pytest.mark.parametrize("shop, pin", [("alpha", "123"), ("alpha", ""), ("../x", "1234"), ("Alpha", "1234")])
def test_bad_pins_and_shop_names_are_refused(auth_file, shop, pin):
    with pytest.raises(ValueError):
        auth.set_pin(shop, pin, auth_file)


def test_a_corrupt_auth_file_locks_everyone_out_instead_of_crashing(auth_file):
    auth_file.parent.mkdir(parents=True)
    auth_file.write_text("{not json", encoding="utf-8")
    assert not auth.check_pin("alpha", "1234", auth_file)


def test_admin_password_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert not auth.check_admin("anything") and not auth.check_admin("")
    monkeypatch.setenv("ADMIN_PASSWORD", "your-admin-password-here")
    assert not auth.check_admin("your-admin-password-here")          # the placeholder never counts
    monkeypatch.setenv("ADMIN_PASSWORD", "correct horse")
    assert auth.check_admin("correct horse") and not auth.check_admin("correct hors")


def test_parse_basic():
    import base64
    ok = "Basic " + base64.b64encode("shop:1234".encode()).decode()
    assert auth.parse_basic(ok) == ("shop", "1234")
    assert auth.parse_basic("Basic " + base64.b64encode(b"user:pa:ss").decode()) == ("user", "pa:ss")
    for bad in (None, "", "Bearer abc", "Basic !!!notbase64", "Basic " + base64.b64encode(b"nocolon").decode()):
        assert auth.parse_basic(bad) is None


def test_throttle_locks_after_repeated_failures_then_releases():
    clock = [100.0]
    t = auth.Throttle(max_failures=3, lock_sec=60, clock=lambda: clock[0])
    key = ("1.2.3.4", "alpha")
    assert t.allowed(key)
    t.fail(key); t.fail(key)
    assert t.allowed(key)
    t.fail(key)
    assert not t.allowed(key)
    assert t.allowed(("1.2.3.4", "beta")) and t.allowed(("9.9.9.9", "alpha"))     # only that pair
    clock[0] += 61
    assert t.allowed(key)


def test_throttle_success_clears_the_count():
    t = auth.Throttle(max_failures=3)
    key = ("ip", "s")
    t.fail(key); t.fail(key); t.ok(key); t.fail(key); t.fail(key)
    assert t.allowed(key)


# ---- store -----------------------------------------------------------------

def sample_order(call_id="c1", when=NOW, total=285, status="confirmed", **extra):
    return {"call_id": call_id, "time": when.isoformat(), "language": "hi-IN", "status": status,
            "customer": "Ramesh", "items": [{"name": "Rice", "qty": 2, "unit": "kg", "line_total": total}],
            "total": total, "payment": "cash", **extra}


def test_an_order_round_trips(tmp_path):
    path = store.write_order("alpha", sample_order(), tmp_path)
    assert path.name == "order_c1.json" and path.parent.name == "alpha"
    records, problems = store.read_records("alpha", "order", tmp_path)
    assert problems == [] and records[0]["_id"] == "c1" and records[0]["total"] == 285


@pytest.mark.parametrize("call_id", ["", "../x", "a/b", "a b", "x" * 65, "ü"])
def test_call_ids_cannot_escape_the_folder(tmp_path, call_id):
    with pytest.raises(ValueError):
        store.write_order("alpha", sample_order(call_id=call_id), tmp_path)


def test_unreadable_files_are_skipped_and_reported(tmp_path):
    store.write_order("alpha", sample_order("good"), tmp_path)
    (tmp_path / "alpha" / "order_broken.json").write_text("{nope", encoding="utf-8")
    (tmp_path / "alpha" / "order_list.json").write_text("[1,2]", encoding="utf-8")
    snap = store.snapshot("alpha", NOW, tmp_path)
    assert [o["id"] for o in snap["orders"]] == ["good"]
    assert len(snap["problems"]) == 2 and "order_broken.json" in snap["problems"][0] + snap["problems"][1]


def test_an_empty_shop_gives_an_empty_snapshot(tmp_path):
    snap = store.snapshot("alpha", NOW, tmp_path)
    assert snap["orders"] == [] and snap["loans"] == [] and snap["ledger"] == []
    assert snap["summary"]["orders_today"] == 0 and snap["summary"]["udhaar_outstanding"] == 0


def test_orders_come_back_newest_first(tmp_path):
    for i, hours in enumerate([5, 1, 3]):
        store.write_order("alpha", sample_order(f"c{i}", NOW - timedelta(hours=hours)), tmp_path)
    assert [o["id"] for o in store.snapshot("alpha", NOW, tmp_path)["orders"]] == ["c1", "c2", "c0"]


def test_today_is_counted_in_indian_time(tmp_path):
    just_after_midnight = datetime(2026, 11, 3, 0, 20, tzinfo=store.IST)
    late_yesterday = just_after_midnight - timedelta(minutes=40)       # 23:40 IST on Nov 2
    store.write_order("alpha", sample_order("a", just_after_midnight, total=100), tmp_path)
    store.write_order("alpha", sample_order("b", late_yesterday, total=50), tmp_path)
    s = store.snapshot("alpha", just_after_midnight + timedelta(hours=1), tmp_path)["summary"]
    assert s["orders_today"] == 1 and s["sales_today"] == 100 and s["orders_total"] == 2


def test_incomplete_orders_do_not_count_as_sales_but_need_attention(tmp_path):
    store.write_order("alpha", sample_order("ok", total=100), tmp_path)
    store.write_order("alpha", sample_order("half", total=999, status="incomplete"), tmp_path)
    store.write_order("alpha", sample_order("wait", total=50, status="credit_pending"), tmp_path)
    s = store.snapshot("alpha", NOW, tmp_path)["summary"]
    assert s["sales_today"] == 150 and s["needs_attention"] == 2


def test_the_ledger_is_summed_and_sorted_by_balance(tmp_path):
    store.write_ledger("alpha", {"customers": {
        "a": {"name": "Asha", "balance": 100, "credit_limit": 500},
        "b": {"name": "Bala", "balance": 700, "credit_limit": 1000},
        "c": {"name": "Chitra", "balance": 0, "credit_limit": 500},
        "d": "garbage",
    }}, tmp_path)
    snap = store.snapshot("alpha", NOW, tmp_path)
    assert [c["name"] for c in snap["ledger"]] == ["Bala", "Asha", "Chitra"]
    assert snap["summary"]["udhaar_outstanding"] == 800 and snap["summary"]["customers_owing"] == 2


def test_numbers_that_arrive_as_text_do_not_crash_the_snapshot(tmp_path):
    store.write_order("alpha", sample_order("x", total="not a number"), tmp_path)
    assert store.snapshot("alpha", NOW, tmp_path)["orders"][0]["total"] == 0


def test_writes_are_atomic_no_temp_files_left(tmp_path):
    store.write_order("alpha", sample_order(), tmp_path)
    assert [p.name for p in (tmp_path / "alpha").iterdir()] == ["order_c1.json"]


# ---- demo data -------------------------------------------------------------

def test_demo_data_is_marked_synthetic_and_adds_up(tmp_path):
    orders, loans, ledger = demo_data.build(NOW)
    assert orders and loans and ledger["customers"]
    for o in orders:
        assert o["synthetic"] is True
        assert o["total"] == sum(i["line_total"] for i in o["items"])
        assert all(i["line_total"] == i["qty"] * i["unit_price"] for i in o["items"])
        if o["payment"] == "udhaar" and o["balance_before"] is not None:
            assert o["balance_after"] == o["balance_before"] + o["total"]
    for l in loans:
        assert l["synthetic"] is True
        expected = quote(l["margin_money"]).to_dict()
        assert {k: l[k] for k in expected} == expected          # the stored quote is the calculator's


def test_demo_ledger_agrees_with_the_demo_orders():
    orders, _, ledger = demo_data.build(NOW)
    ramesh = next(o for o in orders if o["customer"] == "Ramesh" and o["payment"] == "udhaar")
    assert ledger["customers"]["ramesh"]["balance"] == ramesh["balance_after"] == 685
    for c in ledger["customers"].values():
        assert 0 <= c["balance"] <= c["credit_limit"]


def test_seeding_fills_the_dashboard_and_reset_wipes_first(tmp_path):
    n = demo_data.seed("alpha", tmp_path, now=NOW)
    snap = store.snapshot("alpha", NOW, tmp_path)
    assert n == len(snap["orders"]) + len(snap["loans"])
    assert snap["summary"]["orders_today"] > 0 and snap["summary"]["udhaar_outstanding"] > 0
    stray = tmp_path / "alpha" / "order_stray.json"
    stray.write_text("{}", encoding="utf-8")
    demo_data.seed("alpha", tmp_path, reset=True, now=NOW)
    assert not stray.exists()


def test_seeding_refuses_a_bad_shop_name(tmp_path):
    with pytest.raises(ValueError):
        demo_data.seed("../evil", tmp_path)


def test_yesterday_is_compared_up_to_the_same_time_of_day(tmp_path):
    # NOW is 15:30 IST. Yesterday's 10:00 order is before that time; its 18:00 order is not.
    store.write_order("alpha", sample_order("early", NOW - timedelta(days=1, hours=5, minutes=30), total=100), tmp_path)
    store.write_order("alpha", sample_order("late", NOW - timedelta(days=1) + timedelta(hours=2, minutes=30), total=400), tmp_path)
    store.write_order("alpha", sample_order("today", NOW - timedelta(hours=1), total=70), tmp_path)
    s = store.snapshot("alpha", NOW, tmp_path)["summary"]
    assert s["orders_yesterday"] == 2 and s["sales_yesterday"] == 500                  # the whole day, as before
    assert s["orders_yesterday_same_time"] == 1 and s["sales_yesterday_same_time"] == 100
    assert s["orders_today"] == 1 and s["sales_today"] == 70


def test_same_time_figures_skip_incomplete_orders_in_sales(tmp_path):
    store.write_order("alpha", sample_order("half", NOW - timedelta(days=1, hours=3), total=999, status="incomplete"), tmp_path)
    s = store.snapshot("alpha", NOW, tmp_path)["summary"]
    assert s["orders_yesterday_same_time"] == 1 and s["sales_yesterday_same_time"] == 0


def test_list_folders_includes_a_shop_with_no_config_but_list_shops_does_not(tmp_path):
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "config.yaml").write_text("system_prompt: x", encoding="utf-8")
    (tmp_path / "noconfig").mkdir()
    (tmp_path / "Bad Name").mkdir()
    (tmp_path / "a").mkdir()                                  # too short to be a shop name
    (tmp_path / "README.md").write_text("not a shop", encoding="utf-8")
    assert shops.list_shops(tmp_path) == ["ok"]
    assert shops.list_folders(tmp_path) == ["noconfig", "ok"]
    assert shops.list_folders(tmp_path / "missing") == []
