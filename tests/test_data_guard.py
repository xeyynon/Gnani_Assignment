"""
The guard in conftest.py: no test may write into the real data/ folder.

    python -m pytest tests/test_data_guard.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import admin_actions, auth, shops  # noqa: E402

REAL_DATA = shops.PROJECT_ROOT / "data"


def test_the_default_files_point_at_a_throwaway_folder_not_the_real_one():
    for path in (admin_actions.LOG_FILE, admin_actions.STATE_FILE, auth.AUTH_FILE):
        assert REAL_DATA not in path.parents, f"{path} is inside the real data folder"


def test_writing_with_the_defaults_leaves_the_real_data_folder_alone():
    before = {p.name: p.stat().st_mtime_ns for p in REAL_DATA.glob("*")} if REAL_DATA.is_dir() else {}
    admin_actions.log_event("create_shop", "guard_test", "should not reach the real log")      # no path given: uses the default
    auth.set_pin("guard_test", "1234")                                                         # likewise
    after = {p.name: p.stat().st_mtime_ns for p in REAL_DATA.glob("*")} if REAL_DATA.is_dir() else {}
    assert before == after
    assert admin_actions.recent_activity(5)[0]["shop"] == "guard_test"                         # it did write, but to the throwaway one
    if (REAL_DATA / "admin_log.jsonl").is_file():
        assert "guard_test" not in (REAL_DATA / "admin_log.jsonl").read_text(encoding="utf-8")
    if (REAL_DATA / "auth.json").is_file():
        assert "guard_test" not in json.loads((REAL_DATA / "auth.json").read_text(encoding="utf-8")).get("shops", {})
