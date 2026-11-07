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

Noise level (--noise N): the SNR is N dB relative to the whole-clip RMS of the speech clips, that is the RMS over ALL
samples (silence inside the clips included) of ALL clips of the FULL script, never of an --only subset, so the noise is
the same however many calls are run. The definition is printed and saved in the result file as "snr_definition".
The speech clips are cached in evaluation/audio/<script>/; each has a <name>.wav.json sidecar with a hash of
(text, tts_lang, voice), and a clip whose sidecar does not match (the script text was edited) is made again. A clip
with no sidecar is accepted as an older cached clip.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


SNR_DEFINITION = ("SNR relative to the whole-clip RMS of the speech clips (RMS over all samples, silence in the clips included, "
                  "of all clips of the full script)")


def _voice() -> str:
    try:
        from dukaan_dost import tts_gnani
        return tts_gnani.VOICE
    except Exception:
        return os.getenv("GNANI_TTS_VOICE", "Shivani")


def clip_hash(text, tts_lang, voice=None) -> str:
    return hashlib.sha256(json.dumps([text, tts_lang, voice if voice is not None else _voice()], ensure_ascii=False).encode("utf-8")).hexdigest()


def _synthesize(text, tts_lang) -> bytes:
    from dukaan_dost import tts_gnani
    stream = tts_gnani.start_streaming_synthesis(text, tts_lang)
    pcm = b"".join(stream.chunks())
    if stream.failed or not pcm:
        raise RuntimeError(f"synthesis failed for {text!r}: {stream._error}")
    return pcm


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def synth_wav(text, tts_lang, path: Path):
    """Makes the clip unless a cached one is for the same text, language and voice. A cached clip with no sidecar
    (<name>.wav.json) is taken as it is and given one."""
    side = path.with_name(path.name + ".json")
    want = clip_hash(text, tts_lang)
    if path.exists():
        try:
            have = json.loads(side.read_text(encoding="utf-8")).get("hash") if side.exists() else None
        except (OSError, ValueError):
            have = None
        if have == want:
            return
        if not side.exists():                              # a clip made before sidecars existed: keep it
            _atomic_write(side, json.dumps({"hash": want, "text": text, "tts_lang": tts_lang, "voice": _voice(), "legacy": True},
                                           ensure_ascii=False).encode("utf-8"))
            return
        print(f"script text, language or voice changed for {path.name}; making the clip again")
    pcm = _synthesize(text, tts_lang)
    path.parent.mkdir(parents=True, exist_ok=True)
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(pcm)
    _atomic_write(path, buf.getvalue())
    _atomic_write(side, json.dumps({"hash": want, "text": text, "tts_lang": tts_lang, "voice": _voice()}, ensure_ascii=False).encode("utf-8"))


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
    """RMS over all samples of all the clips, silence inside the clips included (the plain whole-clip RMS of the speech)."""
    total, count = 0.0, 0
    for p in wavs:
        with wave.open(str(p), "rb") as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
        total += float(np.sum(a ** 2)); count += len(a)
    return float(np.sqrt(total / count)) if count else 1000.0


def llm_from_log(log_path: Path, env_model=None) -> dict:
    """The provider and model the agent really used, from its startup line 'LLM=<model> (<provider>) ...'."""
    try:
        text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    m = re.search(r"LLM=(\S+)\s*\(([^)]*)\)", text)
    if m:
        return {"model": m.group(1), "llm_provider": m.group(2), "model_source": "agent log"}
    if env_model:
        return {"model": env_model, "llm_provider": "unknown", "model_source": "LLM_MODEL"}
    return {"model": "unknown", "llm_provider": "unknown", "model_source": "unknown"}


def keep_awake(on: bool = True) -> bool:
    """Windows only: ask the system not to go to sleep while this process runs. A laptop that slept for 26 minutes in the
    middle of a run (2026-11-05) froze the agent and the scripted caller, and the runner's wall-clock timeout then ended
    the run half done. Nothing is changed permanently: the request ends with the process. Returns whether it was set."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        flags = 0x80000000 | (0x00000001 if on else 0)          # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        return bool(ctypes.windll.kernel32.SetThreadExecutionState(flags))
    except Exception:
        return False


def main():
    keep_awake(True)
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
    all_calls = script["calls"]
    calls = all_calls
    if args.only:
        keep = set(args.only.split(","))
        calls = [c for c in calls if c["id"] in keep]

    work = ROOT / "evaluation" / "audio" / Path(args.script).stem
    plan_calls = []
    for c in (all_calls if args.noise is not None else calls):       # the noise level needs every clip of the script, not just the --only ones
        for i, t in enumerate(c["turns"]):
            synth_wav(t["text"], t.get("tts_lang", c.get("tts_lang", "hi-IN")), work / f"{c['id']}_{i}.wav")
    for c in calls:
        turns = []
        for i, t in enumerate(c["turns"]):
            wavp = work / f"{c['id']}_{i}.wav"
            turns.append({"audio": str(wavp), "text": t["text"], **({"barge_in_after_sec": t["barge_in_after_sec"]} if t.get("barge_in_after_sec") is not None else {})})
        plan_calls.append({"id": c["id"], "shop": c.get("shop", "dukaan_dost"), "turns": turns})

    out = Path(args.out).resolve()
    raw_results = out.with_suffix(".raw.json")
    orders_dir = work / ("orders_noisy" if args.noise is not None else "orders_clean")
    if orders_dir.exists():
        for f in orders_dir.rglob("*"):
            if f.is_file():
                f.unlink()
    snr_info = {"snr_definition": None}
    plan = {"results": str(raw_results), "min_turn_sec": args.min_turn_sec, "quiet_sec": 3.0,
            "response_timeout_sec": 30, "calls": plan_calls}
    if args.noise is not None:
        noise_wav = work / "noise.wav"
        make_noise(noise_wav)
        sp = speech_rms([work / f"{c['id']}_{i}.wav" for c in all_calls for i in range(len(c["turns"]))])
        with wave.open(str(noise_wav), "rb") as w:
            nrms = float(np.sqrt(np.mean(np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) ** 2)))
        gain = (sp / (10 ** (args.noise / 20))) / nrms
        plan["noise"] = {"path": str(noise_wav), "gain": gain}
        snr_info = {"speech_rms": round(sp, 1), "noise_gain": round(gain, 5), "snr_definition": SNR_DEFINITION}
        print(f"speech RMS {sp:.0f} (whole-clip RMS over all {sum(len(c['turns']) for c in all_calls)} clips of the full script), "
              f"noise gain {gain:.3f} for {args.noise} dB SNR: {SNR_DEFINITION}")
    plan_path = work / ("plan_noisy.json" if args.noise is not None else "plan_clean.json")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if raw_results.exists():
        raw_results.unlink()

    env = dict(os.environ, AUDIO_TRANSPORT="replay", REPLAY_PLAN=str(plan_path), ORDERS_DIR=str(orders_dir),
               ORDER_SYNTHETIC="1", PYTHONIOENCODING="utf-8", PYTHONWARNINGS="ignore",
               LLM_FALLBACK_MODEL="off")      # a run measures one model: no silent switch to another when one is rate limited
    log = open(out.with_suffix(".agent.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "dukaan_dost"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    t0 = time.time()
    timed_out = agent_exited_early = False
    try:
        while True:
            if time.time() - t0 >= args.timeout:
                timed_out = True
                break
            if proc.poll() is not None:
                agent_exited_early = True
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

    raw = None
    try:
        raw = json.loads(raw_results.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    agent_log = out.with_suffix(".agent.log")
    if timed_out:
        print(f"TIMED OUT after {args.timeout} s before the scripted calls finished; the results are incomplete")
    if agent_exited_early:
        print("THE AGENT EXITED EARLY; the results are incomplete; see", agent_log)
    calls_done = len(raw["calls"]) if raw else 0
    complete = bool(raw and raw.get("done") and calls_done == len(calls) and not raw.get("aborted"))
    if not complete:
        print(f"INCOMPLETE RUN: {calls_done} of {len(calls)} calls finished")
    result = {"script": str(Path(args.script).name), "noise_snr_db": args.noise, **llm_from_log(agent_log, os.environ.get("LLM_MODEL")),
              "min_turn_sec": args.min_turn_sec, "elapsed_sec": round(time.time() - t0), "complete": complete,
              "timed_out": timed_out, "agent_exited_early": agent_exited_early, "calls_expected": len(calls), "calls_finished": calls_done,
              **snr_info, "run": raw, "orders_dir": str(orders_dir), "expected": {c["id"]: c.get("expected") for c in calls}}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
