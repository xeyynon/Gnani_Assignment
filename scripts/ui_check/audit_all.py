#!/usr/bin/env python3
"""
ui_check/audit_all.py: run the browser audit (audit.mjs) on every page, in both themes, at four widths, and save the report.

    SNAP_PIN=<shop pin> SNAP_ADMIN_PASSWORD=<admin password> python scripts/ui_check/audit_all.py http://127.0.0.1:8861 [snapshots/latest/reports/audit.txt]

Point it at the made-up-data preview (python -m dukaan_dost.preview --port 8861 --no-browser), which prints both secrets.
The sign-in pages are audited signed out, in their idle, wrong-answer and locked states (the page's own showResult draws
each one). Exit code 1 if any run has an error. Needs Node 20+ and Chrome (CHROME=/path/to/chrome overrides the search).
"""

import base64
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WIDTHS = (300, 360, 390, 768, 1280)       # 300 is a 390 px phone at 130% browser zoom
THEMES = ("light", "dark")
SHOP = "demo_kirana"
WRONG = "showResult(401, {wrong: true, remaining: 3})"
LOCKED = "showResult(429, {locked: true, retry_after: 42})"


def basic(user: str, password: str) -> str:
    return base64.b64encode(f"{user}:{password}".encode("utf-8")).decode()


def pages(pin: str, admin_password: str) -> list:
    """(label, path, basic-auth or '', setup snippet or '')"""
    return [
        ("call page", "/", "", ""),
        ("dashboard", f"/s/{SHOP}/dashboard", basic("shop", pin), ""),
        ("dashboard (calls)", f"/s/{SHOP}/dashboard#calls", basic("shop", pin), ""),
        ("admin", "/admin", basic("admin", admin_password), ""),
        ("sign-in (shop)", f"/s/{SHOP}/dashboard", "", ""),
        ("sign-in (shop, wrong PIN)", f"/s/{SHOP}/dashboard", "", WRONG),
        ("sign-in (shop, locked)", f"/s/{SHOP}/dashboard", "", LOCKED),
        ("sign-in (shop with no PIN)", "/s/no_pin_stores/dashboard", "", ""),
        ("sign-in (admin)", "/admin", "", ""),
        ("sign-in (admin, wrong password)", "/admin", "", WRONG),
    ]


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    base = argv[0].rstrip("/")
    out = Path(argv[1]) if len(argv) > 1 else None
    pin, admin_password = os.environ.get("SNAP_PIN", ""), os.environ.get("SNAP_ADMIN_PASSWORD", "")
    if not pin or not admin_password:
        print("Set SNAP_PIN and SNAP_ADMIN_PASSWORD (the preview prints both).")
        return 2
    lines = ["Browser audit (scripts/ui_check/audit_all.py) of the made-up-data preview. error = must fix, warn = look at.", ""]
    errors = 0
    for label, path, auth, setup in pages(pin, admin_password):
        for theme in THEMES:
            for width in WIDTHS:
                env = {**os.environ, "SETUP": setup} if setup else {k: v for k, v in os.environ.items() if k != "SETUP"}
                cmd = ["node", "--experimental-websocket", str(HERE / "audit.mjs"), base + path, str(width), theme] + ([auth] if auth else [])
                r = subprocess.run(cmd, capture_output=True, text=True, env=env)
                if r.returncode != 0 and not (r.stdout or "").strip():          # Chrome did not start (a clash on its random port, a busy machine): once more
                    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
                for line in (r.stdout or "").splitlines():
                    if line.startswith(("ok ", "ERROR", "warn")):
                        lines.append(f"{label}: {line}")
                if r.returncode != 0:
                    errors += 1
                    if not (r.stdout or "").strip():
                        lines.append(f"{label}: ERROR the audit itself failed: {(r.stderr or '')[:200]}")
        print(f"audited {label}", flush=True)
    summary = f"{errors} run(s) with errors" if errors else "no errors in any run"
    lines += ["", f"{len(pages(pin, admin_password)) * len(THEMES) * len(WIDTHS)} runs: {summary}."]
    text = "\n".join(lines) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(summary)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
