#!/usr/bin/env python3
"""
Runs what GitHub CI runs, on this machine, in a clean virtual environment built only from requirements.txt.
The repository is private, so a run on GitHub cannot be read from here; this finds most of what it would find.

    python scripts/ci_local.py                  # everything
    python scripts/ci_local.py --skip-docker    # without the container build
    python scripts/ci_local.py --keep           # keep the virtual environment for another run

Steps, mirroring .github/workflows/ci.yml:
  install   a fresh venv, `pip install -r requirements.txt pytest ruff vermin`
  tests     python -m pytest -q          (the Python version on this machine; CI also runs 3.10)
  lint      ruff check .
  py310     vermin: the code needs no newer Python than 3.10 (CI runs 3.10, which is not installed here)
  hygiene   scripts/check_repo.py and scripts/check_docs.py
  pages     node --test tests/web/
  docker    docker build, then import the app inside the image (needs a running Docker daemon)
Exit code 0 only if every step that ran passed. Steps it could not run (no Docker daemon) are reported as skipped.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
results = []


def run(name, cmd, cwd=ROOT, env=None, timeout=1500):
    t0 = time.time()
    print(f"\n=== {name}: {' '.join(map(str, cmd))}", flush=True)
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        results.append((name, "FAIL", "timed out"))
        print("timed out")
        return False
    tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])
    print(tail)
    ok = p.returncode == 0
    results.append((name, "ok" if ok else "FAIL", f"{time.time() - t0:.0f}s"))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-docker", action="store_true")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    venv = Path(tempfile.gettempdir()) / "dukaan_ci_venv"
    if venv.exists() and not args.keep:
        shutil.rmtree(venv, ignore_errors=True)
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        if not run("venv", [sys.executable, "-m", "venv", str(venv)]):
            return 1
        if not run("install", [str(py), "-m", "pip", "install", "-q", "-r", "requirements.txt", "pytest", "ruff", "vermin"]):
            return report()

    env = dict(os.environ, DUKAAN_NO_DOTENV="1", PYTHONIOENCODING="utf-8", PYTHONWARNINGS="ignore")
    for var in ("GNANI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "SARVAM_API_KEY", "STT_PROVIDER", "TTS_PROVIDER",
                "LLM_PROVIDER", "AUDIO_TRANSPORT", "REPLAY_PLAN", "LLM_MODEL"):
        env.pop(var, None)                                   # CI has none of these

    run("tests", [str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider"], env=env)
    run("lint", [str(py), "-m", "ruff", "check", "."], env=env)
    vermin = venv / ("Scripts/vermin.exe" if os.name == "nt" else "bin/vermin")
    run("py310", [str(vermin), "--target=3.10-", "--no-tips", "--violations", "dukaan_dost", "scripts", "evaluation", "tests"], env=env)
    # Can every pinned requirement be installed on the Ubuntu runners? (Resolution only; nothing is installed.)
    for version in ("3.10", "3.12"):
        scratch = Path(tempfile.gettempdir()) / f"dukaan_resolve_{version}"
        shutil.rmtree(scratch, ignore_errors=True)
        run(f"linux wheels py{version}", [str(py), "-m", "pip", "install", "--dry-run", "--quiet", "--only-binary=:all:",
                                          "--python-version", version, "--platform", "manylinux2014_x86_64",
                                          "--platform", "manylinux_2_28_x86_64", "--platform", "any",
                                          "--implementation", "cp", "--target", str(scratch), "-r", "requirements.txt"], env=env)
    run("hygiene: repo", [str(py), "scripts/check_repo.py"], env=env)
    run("hygiene: docs", [str(py), "scripts/check_docs.py"], env=env)
    if shutil.which("node"):
        run("pages", ["node", "--test", "tests/web/"], env=env)
    else:
        results.append(("pages", "skipped", "node not installed"))

    if args.skip_docker or not shutil.which("docker"):
        results.append(("docker", "skipped", "not requested or not installed"))
    else:
        up = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if up.returncode != 0:
            results.append(("docker", "skipped", "the Docker daemon is not running"))
        elif run("docker build", ["docker", "build", "-t", "dukaan-dost:ci", "."], timeout=1800):
            run("docker import", ["docker", "run", "--rm", "dukaan-dost:ci", "python", "-c", "import dukaan_dost.app"])
    return report()


def report() -> int:
    print("\n=== summary")
    for name, status, note in results:
        print(f"  {status:8} {name:16} {note}")
    return 0 if all(s in ("ok", "skipped") for _, s, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
