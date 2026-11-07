"""
preview.py

Look at the shopkeeper dashboard and the admin dashboard without any keys or credentials:

    python -m dukaan_dost.preview                 # serves it on http://127.0.0.1:8765
    python -m dukaan_dost.preview --port 9000 --no-browser

It starts only the web server (no speech, no language model) with three made-up shops (one
ready, one with no PIN, one broken) and made-up orders, loan enquiries and credit balances,
then opens the dashboard. The admin page is at /admin (user admin, password admin1111) and everything on it works, on the
made-up shops in the temporary folder. Everything
lives in a temporary folder that is deleted when you stop it, so it never touches
shops/, orders/ or data/. Press Ctrl+C to stop.
"""

import argparse
import json
import os
import shutil
import tempfile
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from . import admin, auth, dashboard, demo_data, shops, store
from .knowledge_retriever import CORE_FILENAME, KNOWLEDGE_FILES
from .transport_websocket import WebSocketTransport

SHOP = "demo_kirana"
TITLE = "Demo Kirana"
PIN = "1111"
ADMIN_PASSWORD = "admin1111"


_STARTED = time.monotonic()


def _pretend_calls() -> list:
    """The preview has no agent, so it shows a made-up call that comes and goes (40 s on, 20 s off)."""
    t = int(time.monotonic() - _STARTED) % 60
    return [{"shop": SHOP, "seconds": t}] if t < 40 else []


def _complete_shop(folder: Path) -> None:
    """Give a preview shop the files a real one has (tiny ones), so the admin page can show it as ready."""
    for name in KNOWLEDGE_FILES:
        (folder / "knowledge" / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / "knowledge" / name).write_text("## Preview\nMade-up text.\n", encoding="utf-8")
    (folder / "knowledge" / CORE_FILENAME).parent.mkdir(parents=True, exist_ok=True)
    (folder / "knowledge" / CORE_FILENAME).write_text("# Preview shop\n", encoding="utf-8")
    item = {"sku": "RICE-1KG", "category": "staples", "unit": "kg", "price": 60, "in_stock": True,
            "name": {"en": "Rice", "hi": "चावल", "te": "బియ్యం"}, "pack": "per kg", "aliases": ["rice", "chawal"]}
    (folder / "stock.json").write_text(json.dumps({"currency": "INR", "items": [item]}, ensure_ascii=False), encoding="utf-8")


def build(host: str = "127.0.0.1", port: int = 8765):
    """Start the preview server. Returns (transport, temp_dir); the caller closes and deletes them."""
    tmp = Path(tempfile.mkdtemp(prefix="dukaan_preview_"))
    shops_root, orders_root = tmp / "shops", tmp / "orders"
    (shops_root / SHOP).mkdir(parents=True)
    (shops_root / SHOP / "config.yaml").write_text(
        f'system_prompt: "Preview only."\nfallback_messages:\n  en-in: "Sorry."\ndisplay_name: "{TITLE}"\n',
        encoding="utf-8")
    for name, config in (("no_pin_stores", 'system_prompt: "Preview only."\nfallback_messages:\n  en-in: "Sorry."\ndisplay_name: "Corner Store (no PIN yet)"\n'),
                         ("broken_shop", "")):                     # one with no PIN, one with an empty config.yaml
        (shops_root / name).mkdir()
        (shops_root / name / "config.yaml").write_text(config, encoding="utf-8")
    _complete_shop(shops_root / SHOP)
    _complete_shop(shops_root / "no_pin_stores")      # works, but no PIN: "needs attention"
    auth.AUTH_FILE = tmp / "auth.json"           # keep the preview's PINs out of data/auth.json
    auth.set_pin(SHOP, PIN, auth.AUTH_FILE)
    auth.set_pin("broken_shop", PIN, auth.AUTH_FILE)
    os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD   # for this process only; the preview is a throwaway
    demo_data.seed(SHOP, orders_root, now=datetime.now(store.IST))

    transport = WebSocketTransport(host=host, port=port)
    transport.configure(default_shop=SHOP, shop_exists=lambda n: shops.exists(n, shops_root),
                        shop_title=lambda n: shops.display_name(n, shops_root))
    transport.add_http_handler(lambda path, headers, remote: dashboard.handle(
        path, headers, remote, shops_root=shops_root, orders_root=orders_root, live_calls=_pretend_calls))
    state_path = tmp / "admin_state.json"        # the preview's "marked solved" list and activity log; never the real data/ files
    log_path = tmp / "admin_log.jsonl"
    transport.add_http_handler(lambda path, headers, remote: admin.handle(
        path, headers, remote, shops_root=shops_root, orders_root=orders_root, live_calls=_pretend_calls,
        auth_path=auth.AUTH_FILE, state_path=state_path, log_path=log_path))
    transport.add_ws_handler(admin.WS_PATH, admin.make_ws_handler(
        shops_root=shops_root, orders_root=orders_root, auth_path=auth.AUTH_FILE, state_path=state_path, log_path=log_path))
    try:
        transport.start()
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return transport, tmp


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview the shopkeeper dashboard with made-up data.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = parser.parse_args()

    transport, tmp = build(args.host, args.port)
    url = f"{transport.url}/s/{SHOP}/dashboard"
    print(f"Dashboard preview: {url}")
    print(f"  password (PIN): {PIN}     (the sign-in page asks for it)")
    print(f"  admin page: {transport.url}/admin   (user admin, password {ADMIN_PASSWORD})")
    print("  All data is made up. Press Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
