"""
preview.py

Look at the shopkeeper dashboard without any keys or credentials:

    python -m dukaan_dost.preview                 # serves it on http://127.0.0.1:8765
    python -m dukaan_dost.preview --port 9000 --no-browser

It starts only the web server (no speech, no language model) with one made-up shop and
made-up orders, loan enquiries and credit balances, then opens the dashboard. Everything
lives in a temporary folder that is deleted when you stop it, so it never touches
shops/, orders/ or data/. Press Ctrl+C to stop.
"""

import argparse
import shutil
import tempfile
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from . import auth, dashboard, demo_data, shops, store
from .transport_websocket import WebSocketTransport

SHOP = "demo_kirana"
TITLE = "Demo Kirana"
PIN = "1111"


def build(host: str = "127.0.0.1", port: int = 8765):
    """Start the preview server. Returns (transport, temp_dir); the caller closes and deletes them."""
    tmp = Path(tempfile.mkdtemp(prefix="dukaan_preview_"))
    shops_root, orders_root = tmp / "shops", tmp / "orders"
    (shops_root / SHOP).mkdir(parents=True)
    (shops_root / SHOP / "config.yaml").write_text(
        f'system_prompt: "Preview only."\nfallback_messages:\n  en-in: "Sorry."\ndisplay_name: "{TITLE}"\n',
        encoding="utf-8")
    auth.AUTH_FILE = tmp / "auth.json"           # keep the preview's PIN out of data/auth.json
    auth.set_pin(SHOP, PIN, auth.AUTH_FILE)
    demo_data.seed(SHOP, orders_root, now=datetime.now(store.IST))

    transport = WebSocketTransport(host=host, port=port)
    transport.configure(default_shop=SHOP, shop_exists=lambda n: shops.exists(n, shops_root),
                        shop_title=lambda n: shops.display_name(n, shops_root))
    transport.add_http_handler(lambda path, headers, remote: dashboard.handle(
        path, headers, remote, shops_root=shops_root, orders_root=orders_root))
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
    print(f"  password (PIN): {PIN}     (the browser asks for it; any user name works)")
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
