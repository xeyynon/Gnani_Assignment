#!/usr/bin/env python3
"""
Runs scripted calls through the REAL agent (voice detection, Prisma, the language model, the order code,
Timbre) with no browser: a call script is turned into speech by Timbre, played into the agent by the replay
transport (dukaan_dost/transport_replay.py), and what happened is written to a results file.

    python evaluation/run_calls.py evaluation/scripts/smoke.json --out evaluation/results/run_smoke.json
    python evaluation/run_calls.py evaluation/scripts/orders.json --noise 10 --out ...      # noisy copy

Script file: {"calls": [{"id", "shop", "lang", "turns": [{"text", "tts_lang", "barge_in_after_sec"?}],
                          "expected": {...}}]}
All speech is synthetic (Timbre) and the noise is generated here, never recorded.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def synth_wav(text, tts_lang, path: Path):
    from dukaan_dost import tts_gnani
    if path.exists():
        return
    stream = tts_gnani.start_streaming_synthesis(text, tts_lang)
    pcm = b"".join(stream.chunks())
    if stream.failed or not pcm:
        raise RuntimeError(f"synthesis failed for {text!r}: {stream._error}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(pcm)


def make_noise(path: Path, seconds=60, seed=7):
    """Steady synthetic background: low rumble, broadband hiss and a hum, loosely like a shop with a fan and traffic."""
    rng = np.random.default_rng(seed)
    n = 16000 * seconds
    hiss = rng.normal(0, 1, n)
    rumble = np.convolve(rng.normal(0, 1, n), np.ones(80) / 80, mode="same") * 6
    t = np.arange(n) / 16000
    hum = 2 * np.sin(2 * np.pi * 100 * t) + np.sin(2 * np.pi * 50 * t)
    x = hiss * 0.6 + rumble + hum
    x = x / np.sqrt(np.mean(x ** 2))                 # unit RMS
    pcm = (x * 3000).astype(np.int16)                # RMS 3000 before scaling
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(pcm.tobytes())


def speech_rms(wavs):
    vals = []
    for p in wavs:
        with wave.open(str(p), "rb") as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
        a = a[np.abs(a) > 300]                        # only the speech, not the silence in the clip
        if len(a):
            vals.append(np.mean(a ** 2))
    return float(np.sqrt(np.mean(vals))) if vals else 1000.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--noise", type=float, default=None, help="mix steady noise at this SNR in dB")
    ap.add_argument("--min-turn-sec", type=float, default=22, help="least gap between turns (the model's rate limit)")
    ap.add_argument("--only", default=None, help="comma-separated call ids")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    from dukaan_dost import envfile
    envfile.load()
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    calls = script["calls"]
    if args.only:
        keep = set(args.only.split(","))
        calls = [c for c in calls if c["id"] in keep]

    work = ROOT / "evaluation" / "audio" / Path(args.script).stem
    plan_calls = []
    for c in calls:
        turns = []
        for i, t in enumerate(c["turns"]):
            wavp = work / f"{c['id']}_{i}.wav"
            synth_wav(t["text"], t.get("tts_lang", c.get("tts_lang", "hi-IN")), wavp)
            turns.append({"audio": str(wavp), "text": t["text"], **({"barge_in_after_sec": t["barge_in_after_sec"]} if t.get("barge_in_after_sec") is not None else {})})
        plan_calls.append({"id": c["id"], "shop": c.get("shop", "dukaan_dost"), "turns": turns})

    out = Path(args.out).resolve()
    raw_results = out.with_suffix(".raw.json")
    orders_dir = work / ("orders_noisy" if args.noise is not None else "orders_clean")
    if orders_dir.exists():
        for f in orders_dir.rglob("*"):
            if f.is_file():
                f.unlink()
    plan = {"results": str(raw_results), "min_turn_sec": args.min_turn_sec, "quiet_sec": 3.0,
            "response_timeout_sec": 30, "calls": plan_calls}
    if args.noise is not None:
        noise_wav = work / "noise.wav"
        make_noise(noise_wav)
        sp = speech_rms([Path(t["audio"]) for c in plan_calls for t in c["turns"]])
        with wave.open(str(noise_wav), "rb") as w:
            nrms = float(np.sqrt(np.mean(np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) ** 2)))
        gain = (sp / (10 ** (args.noise / 20))) / nrms
        plan["noise"] = {"path": str(noise_wav), "gain": gain}
        print(f"speech RMS {sp:.0f}, noise gain {gain:.3f} for {args.noise} dB SNR")
    plan_path = work / ("plan_noisy.json" if args.noise is not None else "plan_clean.json")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if raw_results.exists():
        raw_results.unlink()

    env = dict(os.environ, AUDIO_TRANSPORT="replay", REPLAY_PLAN=str(plan_path), ORDERS_DIR=str(orders_dir),
               ORDER_SYNTHETIC="1", PYTHONIOENCODING="utf-8", PYTHONWARNINGS="ignore")
    log = open(out.with_suffix(".agent.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "dukaan_dost"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    t0 = time.time()
    try:
        while time.time() - t0 < args.timeout:
            if proc.poll() is not None:
                print("the agent exited early; see", out.with_suffix(".agent.log"))
                break
            try:
                if json.loads(raw_results.read_text(encoding="utf-8")).get("done"):
                    break
            except (OSError, ValueError):
                pass
            time.sleep(3)
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()

    result = {"script": str(Path(args.script).name), "noise_snr_db": args.noise, "model": os.environ.get("LLM_MODEL") or "default",
              "min_turn_sec": args.min_turn_sec, "elapsed_sec": round(time.time() - t0),
              "run": json.loads(raw_results.read_text(encoding="utf-8")) if raw_results.exists() else None,
              "orders_dir": str(orders_dir), "expected": {c["id"]: c.get("expected") for c in calls}}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
