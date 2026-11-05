#!/usr/bin/env python3
"""
ui_check/snapshot_release.py: screenshot what the pages looked like at one release, into snapshots/history/<label>/.

    python scripts/ui_check/snapshot_release.py <rev> <label> [--harness REV] [--static] [--working-tree] [--out snapshots/history]

    python scripts/ui_check/snapshot_release.py build-1005 04-build-1005
    python scripts/ui_check/snapshot_release.py build-1003 02-build-1003 --harness 86d706a   # 1003 had no preview; the next commit has the same pages and one
    python scripts/ui_check/snapshot_release.py build-1002 01-build-1002 --static            # 1002 was a call page and nothing else: serve its file as it was
    python scripts/ui_check/snapshot_release.py HEAD 11-build-1015 --working-tree            # the files as they are now, including what is not committed

How it works: the revision is unpacked with `git archive` into a temporary folder (nothing in your repository's git state changes),
that release's own `python -m dukaan_dost.preview` runs from there on a free port, the current snapshots.mjs takes the pictures, and
the temporary folder is deleted. So each picture is the page as that release really drew it, with that release's own made-up data.

What is taken per release: the landing view of each page that existed (call page, shop dashboard, admin, and the two sign-in pages
once login.py existed), in light and dark, at phone 390 px and desktop 1280 px. snapshots/CHANGES.md is built from these by
scripts/ui_check/history_index.py. Needs Node 20+ and Chrome (CHROME=/path/to/chrome overrides the search).
"""

import argparse
import base64
import http.server
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEVICES = [["phone", 390, 844], ["desktop", 1280, 900]]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def unpack(rev: str, dest: Path) -> None:
    data = subprocess.run(["git", "archive", "--format=tar", rev], cwd=ROOT, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")


def basic(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode("utf-8")).decode()


def wait_for(url: str, seconds: int = 40) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def start_preview(tree: Path, port: int):
    """Run that release's own preview. Returns (process, found) where found holds what it printed: the dashboard path, the PIN, the admin password."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
    for name in ("ADMIN_PASSWORD",):
        env.pop(name, None)
    proc = subprocess.Popen([sys.executable, "-m", "dukaan_dost.preview", "--port", str(port), "--no-browser"], cwd=tree,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    found, lines = {}, []

    def read():
        for line in proc.stdout:
            lines.append(line)
            m = re.search(r"Dashboard preview: https?://[^/]+(/\S+)", line)
            if m:
                found["dashboard"] = m.group(1)
            m = re.search(r"\(PIN\):\s*(\S+)", line)
            if m:
                found["pin"] = m.group(1)
            m = re.search(r"admin page: https?://[^/]+(/\S*)\s+\(user admin, password (\S+?)\)", line)
            if m:
                found["admin"], found["admin_password"] = m.group(1), m.group(2)

    threading.Thread(target=read, daemon=True).start()
    ok = wait_for(f"http://127.0.0.1:{port}/")
    time.sleep(0.5)
    found["ok"], found["log"] = ok, "".join(lines)
    return proc, found


def serve_static(index: Path, port: int):
    """Release 1002 was the call page alone: serve its one file, with the shop name filled in."""
    page = index.read_text(encoding="utf-8").replace("{{SHOP}}", "Demo Kirana").encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rev")
    ap.add_argument("label")
    ap.add_argument("--harness", help="run this revision's code instead (the pages must be the same)")
    ap.add_argument("--static", action="store_true", help="serve only the call page file (release 1002)")
    ap.add_argument("--working-tree", action="store_true", help="use the files as they are now, committed or not")
    ap.add_argument("--out", default="snapshots/history")
    a = ap.parse_args(argv)

    out = ROOT / a.out / a.label
    if out.exists():
        shutil.rmtree(out)                                   # only ever inside snapshots/history/<label>
    tmp = Path(tempfile.mkdtemp(prefix="dd-release-"))
    port, proc, server = free_port(), None, None
    try:
        if a.working_tree:
            tree, shown_rev = ROOT, "working tree"
        else:
            tree, shown_rev = tmp, a.rev
            unpack(a.harness or a.rev, tmp)
        pages = [{"name": "call-page", "path": "/", "auth": "", "states": [["landing", ""]]}]
        if a.static:
            server = serve_static(tree / "dukaan_dost" / "web" / "index.html", port)
            if not wait_for(f"http://127.0.0.1:{port}/"):
                print("the static page did not come up")
                return 1
        else:
            proc, found = start_preview(tree, port)
            if not found["ok"] or "dashboard" not in found:
                print("the preview of that release did not come up:\n" + found["log"][-1500:])
                return 1
            pages.append({"name": "dashboard", "path": found["dashboard"], "auth": basic("shop", found.get("pin", "")), "states": [["landing", ""]]})
            if "admin" in found:
                pages.append({"name": "admin", "path": found["admin"], "auth": basic("admin", found["admin_password"]), "states": [["landing", ""]]})
            if (tree / "dukaan_dost" / "login.py").exists():                      # the sign-in pages exist from the release that has login.py
                pages.append({"name": "sign-in-shop", "path": found["dashboard"], "auth": "", "states": [["landing", ""]]})
                pages.append({"name": "sign-in-admin", "path": found.get("admin", "/admin"), "auth": "", "states": [["landing", ""]]})
        env = {**os.environ, "SNAP_PAGES": json.dumps(pages), "SNAP_DEVICES": json.dumps(DEVICES), "SNAP_NO_INDEX": "1"}
        r = subprocess.run(["node", "--experimental-websocket", str(ROOT / "scripts" / "ui_check" / "snapshots.mjs"),
                            f"http://127.0.0.1:{port}", str(out)], cwd=ROOT, env=env, capture_output=True, text=True)
        print((r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-800:])
        if not (out / "manifest.json").exists():
            print(r.stderr[-800:])
            return 1
        rev_for_info = "HEAD" if a.working_tree else a.rev
        sha, date, title = (git("log", "-1", "--format=%h%x09%ad%x09%s", "--date=short", rev_for_info).strip().split("\t") + ["", "", ""])[:3]
        (out / "release.json").write_text(json.dumps({
            "label": a.label, "rev": shown_rev, "commit": sha, "date": date, "title": title,
            "ran_code_of": a.harness or ("the working tree" if a.working_tree else a.rev), "pages": [p["name"] for p in pages],
        }, indent=1), encoding="utf-8")
        return 0
    finally:
        if proc is not None:
            proc.terminate()
        if server is not None:
            server.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
