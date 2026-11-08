#!/usr/bin/env python3
"""
One command to bring the phone demo up: the agent in phone mode and a public tunnel to it, with the address to paste into the
Exotel Voicebot applet. You run it yourself, in your own terminal.

    python scripts/phone_demo.py                  # agent on port 8766 + cloudflared tunnel
    python scripts/phone_demo.py --no-tunnel      # just the agent (you bring your own tunnel)
    python scripts/phone_demo.py --model openai/gpt-oss-20b

What it does:
  1. starts `python -m dukaan_dost` with AUDIO_TRANSPORT=telephony on the chosen port (keys come from .env);
  2. starts `cloudflared tunnel --url http://127.0.0.1:<port>` (cloudflared must be installed) and reads the address it gets;
  3. prints the URL for the Exotel applet. The secret is NOT printed: add your TELEPHONY_TOKEN from .env after `token=`;
  4. shows the agent's phone and order lines while a call is on, and stops both when you press Ctrl+C.

The tunnel address changes every time cloudflared starts, so the applet's URL must be edited and saved each time
(flow "Dukaan Dost Voice Agent", Voicebot applet). Set-up of the Exotel account: MD/phone_setup.md.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
SHOW = ("[PHONE]", "[ORDER]", "[STT-GNANI]", "Caller (", "[LOAN]", "[STT]", "rate limited", "ERROR", "Ready:", "listening")


def tunnel_address(text: str) -> str | None:
    """The trycloudflare address in a line of cloudflared's output, or None."""
    m = TUNNEL_RE.search(text or "")
    return m.group(0) if m else None


def applet_url(address: str, shop: str = "dukaan_dost", sample_rate: int = 16000) -> str:
    """The WebSocket address for the Exotel Voicebot applet. The token is left for the person to add."""
    host = address.replace("https://", "").replace("http://", "").strip("/")
    return f"wss://{host}/telephony/exotel?sample-rate={sample_rate}&shop={shop}&token="


def interesting(line: str) -> bool:
    return any(s in line for s in SHOW)


def _pump(proc, label, on_line):
    for raw in iter(proc.stdout.readline, ""):
        line = raw.rstrip()
        if line:
            on_line(label, line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--model", default=None, help="LLM_MODEL for the agent (default: whatever .env says)")
    ap.add_argument("--shop", default="dukaan_dost")
    ap.add_argument("--no-tunnel", action="store_true")
    args = ap.parse_args()

    env = dict(os.environ, AUDIO_TRANSPORT="telephony", AUDIO_PORT=str(args.port), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if args.model:
        env["LLM_MODEL"] = args.model
    cloudflared = None if args.no_tunnel else shutil.which("cloudflared")
    if not args.no_tunnel and cloudflared is None:
        print("cloudflared is not installed (Windows: choco install cloudflared, in an administrator terminal). "
              "Install it, or run with --no-tunnel and bring your own tunnel.")
        return 2

    state = {"address": None, "ready": False}
    lock = threading.Lock()

    def show(label, line):
        if label == "tunnel":
            addr = tunnel_address(line)
            if addr and not state["address"]:
                with lock:
                    state["address"] = addr
                print(f"\n=== tunnel up: {addr}")
                print("=== paste this into the Voicebot applet's URL, then add your TELEPHONY_TOKEN after token= and Save:")
                print("    " + applet_url(addr, args.shop) + "\n", flush=True)
            return
        if "Ready:" in line:
            state["ready"] = True
        if interesting(line):
            print(f"[agent] {line}", flush=True)

    procs = []
    try:
        agent = subprocess.Popen([sys.executable, "-m", "dukaan_dost"], cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        procs.append(agent)
        threading.Thread(target=_pump, args=(agent, "agent", show), daemon=True).start()
        print(f"starting the agent in phone mode on port {args.port} ...", flush=True)
        deadline = time.time() + 90
        while not state["ready"] and time.time() < deadline and agent.poll() is None:
            time.sleep(0.5)
        if agent.poll() is not None:
            print("the agent exited; check the lines above (another agent on that port? use --port)")
            return 1
        if cloudflared:
            tun = subprocess.Popen([cloudflared, "tunnel", "--url", f"http://127.0.0.1:{args.port}"], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            procs.append(tun)
            threading.Thread(target=_pump, args=(tun, "tunnel", show), daemon=True).start()
        else:
            print(f"agent ready on http://127.0.0.1:{args.port}; point your tunnel at it, then use "
                  "wss://<your host>/telephony/exotel?sample-rate=16000&shop=" + args.shop + "&token=<TELEPHONY_TOKEN>", flush=True)
        print("running; call the number. Ctrl+C stops everything.", flush=True)
        while all(p.poll() is None for p in procs):
            time.sleep(1)
        return 0
    except KeyboardInterrupt:
        print("\nstopping ...")
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
