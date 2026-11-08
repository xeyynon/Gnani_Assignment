#!/usr/bin/env python3
"""
Runs evaluation runs on a FROZEN copy of the committed code, scores each one and copies the results back.

Why a copy: a run takes 25 to 45 minutes, and fixes made in the working folder meanwhile (or a colleague's unfinished
work) must not change what is measured. The copy is the working folder's untracked files (the .env with the keys, the audio
cache) with every tracked file put back to its committed state (`git archive HEAD`).

    python evaluation/run_snapshot.py --runs smoke                    # two calls: does the set-up work
    python evaluation/run_snapshot.py --runs search20b                # the 20-call order script, search mode, gpt-oss-20b
    python evaluation/run_snapshot.py --runs credit,noise20 --keep    # several in a row; --keep leaves the copy for inspection

A model's daily token limit (about 200,000 on this account, a rolling 24 hours) is about one full 20-call run, and nothing
else may use that model meanwhile. The runner sets LLM_FALLBACK_MODEL=off, so a run measures one model. A run in which any
request was refused is saved as INVALID_<name> by the scorer and is never quoted.
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# name: (label, model, script, noise dB, run name, result name, extra environment)
RUNS = {
    "smoke": ("smoke, gpt-oss-120b", "openai/gpt-oss-120b", "smoke.json", None, "run_smoke", "smoke_snapshot", {}),
    "search20b": ("clean, search mode, gpt-oss-20b", "openai/gpt-oss-20b", "orders.json", None, "run_search_20b",
                  "orders_clean_search_20b", {"ORDER_CATALOGUE": "search"}),
    "clean20b": ("clean, default mode, gpt-oss-20b", "openai/gpt-oss-20b", "orders.json", None, "run_clean_20b",
                 "orders_clean_20b", {}),
    "search120b": ("clean, search mode, gpt-oss-120b", "openai/gpt-oss-120b", "orders.json", None, "run_search_120b",
                   "orders_clean_search_120b", {"ORDER_CATALOGUE": "search"}),
    "e2e": ("end-to-end conversations, gpt-oss-20b, search mode", "openai/gpt-oss-20b", "e2e_phone.json", None, "run_e2e",
            "e2e_phone_20b", {"ORDER_CATALOGUE": "search"}),
    "credit": ("credit and loans, gpt-oss-120b", "openai/gpt-oss-120b", "credit_loans.json", None, "run_credit_loans",
               "credit_loans_clean_120b", {}),
    "noise20": ("noisy 20 dB, gpt-oss-120b", "openai/gpt-oss-120b", "orders.json", 20, "run_noisy20", "orders_noisy20db_120b", {}),
    "noise15": ("noisy 15 dB, gpt-oss-120b", "openai/gpt-oss-120b", "orders.json", 15, "run_noisy15", "orders_noisy15db_120b", {}),
}

IGNORE = {".git", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "logs", "snapshots",
          ".playwright-mcp"}


def _ignore(_dir, names):
    return {n for n in names if n in IGNORE or n.startswith((".venv", "venv")) or n.endswith(".pyc")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", default="smoke", help="comma-separated names: " + ", ".join(RUNS))
    ap.add_argument("--min-turn-sec", type=float, default=28.0,
                    help="least gap between turns; 28 keeps a 20b run under the 8,000 tokens a minute limit")
    ap.add_argument("--timeout", type=int, default=3000, help="seconds a run may take")
    ap.add_argument("--keep", action="store_true", help="keep the frozen copy afterwards")
    ap.add_argument("--working-tree", action="store_true",
                    help="freeze the files as they are, uncommitted changes included, instead of the committed state; "
                         "use it only to test a change that will be committed unchanged right after")
    args = ap.parse_args()

    names = [n.strip() for n in args.runs.split(",") if n.strip()]
    unknown = [n for n in names if n not in RUNS]
    if unknown:
        print(f"unknown run(s): {', '.join(unknown)}; choose from {', '.join(RUNS)}")
        return 2

    snap = Path(tempfile.mkdtemp(prefix="dukaan_snapshot_"))
    log_path = snap.parent / (snap.name + ".log")

    def say(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    shutil.rmtree(snap)
    shutil.copytree(ROOT, snap, ignore=_ignore)
    if not args.working_tree:
        tar = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(snap)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    state = f"commit {head} plus the uncommitted working tree" if args.working_tree else f"commit {head} exactly as committed"
    (snap / "SNAPSHOT_STATE.txt").write_text(f"{state} ({time.strftime('%Y-%m-%d %H:%M')} IST)\n", encoding="utf-8")
    say(f"frozen copy at {snap}: {state}" + ("" if args.working_tree or not dirty else " (the working folder has uncommitted changes that are NOT in the copy)"))
    say(f"log: {log_path}")

    base_env = dict(os.environ, LLM_PROVIDER="groq", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    failed = 0
    for name in names:
        label, model, script, noise, run_name, result_name, extra = RUNS[name]
        say(f"=== {label}: start")
        env = dict(base_env, LLM_MODEL=model, **extra)
        out = snap / "evaluation" / "audio" / f"{run_name}.json"
        cmd = [sys.executable, "evaluation/run_calls.py", f"evaluation/scripts/{script}", "--out", str(out),
               "--min-turn-sec", str(args.min_turn_sec), "--timeout", str(args.timeout)]
        if noise is not None:
            cmd += ["--noise", str(noise)]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=snap, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        say(f"runner exit {r.returncode} after {round(time.time() - t0)} s\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
        if not out.exists():
            say(f"!!! no run file for {label}; skipping the score")
            failed += 1
            continue
        res = snap / "evaluation" / "results" / f"{result_name}.json"
        s = subprocess.run([sys.executable, "evaluation/score_calls.py", str(out), "--out", str(res)], cwd=snap, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        say(f"scorer exit {s.returncode}\n{s.stdout[-3500:]}\n{s.stderr[-1500:]}")
        agent_log = out.with_suffix(".agent.log")
        refused = agent_log.read_text(encoding="utf-8", errors="replace").count("429 Too Many Requests") if agent_log.exists() else 0
        say(f"requests the model refused (429): {refused}" + ("  -> the scorer marks this run INVALID" if refused else ""))
        for p in (out, out.with_suffix(".raw.json"), agent_log):
            if p.exists():
                shutil.copy2(p, ROOT / "evaluation" / "audio" / p.name)
        banner = res.with_suffix(".md").read_text(encoding="utf-8") if res.with_suffix(".md").exists() else ""
        prefix = "INVALID_" if "**INVALID RUN" in banner else "INCOMPLETE_" if "**INCOMPLETE RUN" in banner else ""
        for p in sorted(res.parent.glob(res.stem + ".*")):
            target = ROOT / "evaluation" / "results" / (prefix + p.name)       # an unusable run is saved as evidence only
            shutil.copy2(p, target)
            say(f"saved evaluation/results/{target.name}")
        say(f"=== {label}: done")
    if not args.keep:
        shutil.rmtree(snap, ignore_errors=True)
    say("ALL DONE" if not failed else f"DONE with {failed} run(s) that produced no file")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
