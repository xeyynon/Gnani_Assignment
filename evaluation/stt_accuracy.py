#!/usr/bin/env python3
"""
How well does Gnani Prisma hear the shop's callers? This sends every turn of the order script (the synthetic Timbre
clips already cached in evaluation/audio/orders) to Prisma on its own: no language model, no Groq tokens, so it can be
run at any time of day. It is the speech half of the evaluation; run_calls.py + score_calls.py measure the whole call.

Four ways of sending the same clip:

    clean / auto      the clip as it is, Prisma chooses the language (what a call does first)
    clean / named     the clip as it is, Prisma is told the language of the call (what the agent's retry does)
    phone / auto      the clip after a simulated telephone line (8 kHz, 300 to 3,400 Hz, mu-law), language chosen
    phone / named     the same, language named

and a fifth, computed from those and not measured on its own:

    pipeline          "auto", and when auto came back empty, "named": the agent's behaviour since 2026-11-07
                      (an approximation: the agent names the call's own language only after the first turn and
                      tries Hindi then Telugu before that)

The phone line is MY simulation, not Exotel's audio; the voices are synthetic Timbre voices, not people. Both limits are
written into the result file. Usage:

    python evaluation/stt_accuracy.py --out evaluation/results/stt_accuracy_prisma     # about 15 to 25 minutes
    python evaluation/stt_accuracy.py --limit 6                                         # a quick look, not saved
"""

import argparse
import json
import os
import sys
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from dukaan_dost import envfile  # noqa: E402

envfile.load()

from dukaan_dost import shops, stock, stt_gnani  # noqa: E402
from evaluation import score_calls as sc  # noqa: E402

AUDIO = ROOT / "evaluation" / "audio" / "orders"
SCRIPT = ROOT / "evaluation" / "scripts" / "orders.json"
SHORT_SEC = 1.6                       # "cash", "that's all", a name: where the language choice matters most
HINT = {"hi-IN": "hi-IN", "hi-en": "hi-IN", "te-IN": "te-IN", "en-IN": "en-IN"}


# ---- audio ------------------------------------------------------------------------------------------------------

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, path
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    return x, rate


def resample(x, src, dst):
    """FFT resampling: keeps only the frequencies the new rate can carry, so going down also low-passes."""
    if src == dst:
        return x
    n_new = int(round(len(x) * dst / src))
    spec = np.fft.rfft(x)
    out = np.zeros(n_new // 2 + 1, dtype=complex)
    k = min(len(spec), len(out))
    out[:k] = spec[:k]
    return np.fft.irfft(out, n_new) * (n_new / len(x))


def mulaw(x, mu=255.0):
    v = np.clip(x / 32768.0, -1, 1)
    enc = np.sign(v) * np.log1p(mu * np.abs(v)) / np.log1p(mu)
    q = np.round((enc + 1) / 2 * 255) / 255 * 2 - 1                            # 8-bit companding
    return np.sign(q) * (1 / mu) * ((1 + mu) ** np.abs(q) - 1) * 32768.0


def phone_line(x, rate):
    y = resample(x, rate, 8000)
    spec = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(len(y), 1 / 8000)
    spec[(freqs < 300) | (freqs > 3400)] = 0                                    # the telephone band
    y = mulaw(np.fft.irfft(spec, len(y)))
    return resample(y, 8000, 16000)


def pcm16(x):
    return np.clip(x, -32768, 32767).astype(np.int16).tobytes()


def hear(pcm: bytes, language: str):
    """(transcript, language tag) as the agent's own client returns it; ("", "ERROR") if the service failed."""
    s = stt_gnani.start_streaming_session(language)
    pcm += b"\x00" * 22400                                                       # 0.7 s of silence: the hangover
    for i in range(0, len(pcm), 960):                                            # 30 ms frames, as in a call
        s.feed(pcm[i:i + 960])
    return s.finish()


# ---- scoring ----------------------------------------------------------------------------------------------------

def score(rows, key, variants):
    n = len(rows)
    empty = sum(1 for r in rows if not r[key].strip())
    exact = sum(1 for r in rows if sc.words(r["ref"], True) == sc.words(r[key], True))
    errors = sum(1 for r in rows if r.get(key + "_error"))
    dist = ref_len = miss = eng = 0
    for r in rows:
        ref, hyp = sc.words(r["ref"], True), sc.words(r[key], True)
        d, n_ref = sc.wer(ref, hyp)
        dist += d
        ref_len += n_ref
        m, e = sc.t_wer(sc.words(r["ref"]), sc.words(r[key]), variants)
        miss += m
        eng += e
    return {"turns": n, "empty": empty, "exact": exact, "exact_ci95": sc.wilson(exact, n), "service_errors": errors,
            "wer": round(dist / ref_len, 3) if ref_len else None,
            "t_wer": round(miss / eng, 3) if eng else None, "english_words": eng}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="path without extension: writes .json and .md")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    calls = json.loads(SCRIPT.read_text(encoding="utf-8"))["calls"]
    shop_dir = shops.shop_dir("dukaan_dost")
    variants = sc.english_variants(stock.load(shop_dir))
    jobs = []
    for c in calls:
        for i, t in enumerate(c["turns"]):
            f = AUDIO / f"{c['id']}_{i}.wav"
            if f.exists():
                jobs.append({"clip": f.stem, "call_lang": c["lang"], "ref": t["text"], "file": f})
    if args.limit:
        jobs = jobs[:args.limit]
    print(f"{len(jobs)} clips x 4 ways = {len(jobs) * 4} Prisma sessions, {args.workers} at a time", flush=True)

    lock = threading.Lock()
    done = [0]

    def run(job):
        x, rate = read_wav(job["file"])
        job["seconds"] = round(len(x) / rate, 2)
        hint = HINT.get(job["call_lang"], "hi-IN")
        clean, phone = pcm16(resample(x, rate, 16000)), pcm16(phone_line(x, rate))
        for name, pcm, lang in (("clean_auto", clean, "indic-auto"), ("clean_named", clean, hint),
                                ("phone_auto", phone, "indic-auto"), ("phone_named", phone, hint)):
            try:
                text, tag = hear(pcm, lang)
            except Exception as e:
                text, tag = "", "ERROR"
                print(f"  {job['clip']} {name}: {e}", flush=True)
            job[name], job[name + "_tag"] = text, tag
            if tag == "ERROR":
                job[name + "_error"] = True
        for side in ("clean", "phone"):                                           # the agent: auto, then named if empty
            auto, named = job[f"{side}_auto"], job[f"{side}_named"]
            job[f"{side}_pipeline"] = auto if auto.strip() else named
        with lock:
            done[0] += 1
            if done[0] % 5 == 0 or done[0] == len(jobs):
                print(f"  {done[0]}/{len(jobs)} clips", flush=True)
        return job

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run, jobs))
    elapsed = round(time.time() - t0)

    keys = ["clean_auto", "clean_named", "clean_pipeline", "phone_auto", "phone_named", "phone_pipeline"]
    groups = {"all turns": rows, f"short turns (up to {SHORT_SEC} s)": [r for r in rows if r["seconds"] <= SHORT_SEC],
              "longer turns": [r for r in rows if r["seconds"] > SHORT_SEC]}
    for lang in ("hi-en", "hi-IN", "te-IN", "en-IN"):
        groups[f"calls in {lang}"] = [r for r in rows if r["call_lang"] == lang]
    result = {"what": "Gnani Prisma alone (no language model) on the synthetic order-script clips",
              "limits": ["synthetic Timbre voices, not people", "the phone line is a simulation (8 kHz, 300-3400 Hz, mu-law), "
                         "not Exotel's audio", "pipeline = auto, then named when auto was empty; an approximation of the agent"],
              "elapsed_sec": elapsed, "shop": "dukaan_dost", "turns": len(rows),
              "service_errors": sum(1 for r in rows for k in keys[:2] + keys[3:5] if r.get(k + "_error")),
              "by_group": {g: {k: score(rs, k, variants) for k in keys} for g, rs in groups.items() if rs},
              "rows": [{k: v for k, v in r.items() if k != "file"} for r in rows]}
    valid = result["service_errors"] == 0
    result["valid"] = valid

    lines = [f"# Prisma alone: {len(rows)} synthetic turns, four ways ({elapsed} s)", "",
             "Synthetic Timbre voices; the phone line is a simulation, not Exotel's audio. " +
             ("" if valid else "**INVALID: the service failed on some sessions; do not quote.** "), ""]
    for g, table in result["by_group"].items():
        lines += [f"## {g}", "", "| way | turns | empty | exactly right | 95% interval | WER | T-WER |", "|---|---|---|---|---|---|---|"]
        for k in keys:
            s = table[k]
            lines.append(f"| {k.replace('_', ' / ')} | {s['turns']} | {s['empty']} | {s['exact']} | "
                         f"{s['exact_ci95'][0]:.0%} to {s['exact_ci95'][1]:.0%} | {s['wer']} | {s['t_wer']} |")
        lines.append("")
    if args.out:
        out = Path(args.out)
        if not valid:
            out = out.with_name("INVALID_" + out.name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
        print(f"saved {out.with_suffix('.json')}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
