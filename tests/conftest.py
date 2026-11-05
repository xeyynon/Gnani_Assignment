"""
Shared test setup. The tests must not depend on whatever keys or provider choices are in the
developer's own .env, so the .env loader is switched off before the package is first imported.

They also must never write into the real data/ folder. The admin dashboard keeps three files there
(the PINs, the list of problems marked solved, the activity log); a test that forgot to point at a
temporary one once left made-up "Shop added" entries in a real activity log. Every test now starts
with all three pointed at a throwaway folder, and a test that wants its own simply sets its own.
"""

import os

os.environ["DUKAAN_NO_DOTENV"] = "1"

import pytest


@pytest.fixture(autouse=True)
def _never_touch_the_real_data_folder(tmp_path_factory, monkeypatch):
    from dukaan_dost import admin_actions, auth
    scratch = tmp_path_factory.mktemp("data_guard")
    monkeypatch.setattr(admin_actions, "LOG_FILE", scratch / "admin_log.jsonl")
    monkeypatch.setattr(admin_actions, "STATE_FILE", scratch / "admin_state.json")
    monkeypatch.setattr(auth, "AUTH_FILE", scratch / "auth.json")
