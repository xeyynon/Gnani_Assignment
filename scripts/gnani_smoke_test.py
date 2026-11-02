#!/usr/bin/env python3
"""
First contact with the real Gnani services. Needs a key (GNANI_API_KEY, from
https://app.gnani.ai/voice). Runs the experiments listed in
MD/pipeline_expectations.md, section 5, through the same backend modules the
agent uses, so a pass here means the agent's own code works against the real
service.

    python scripts/gnani_smoke_test.py tts                 # E2: first-audio time, listen to the WAVs
    python scripts/gnani_smoke_test.py roundtrip           # E3/E6: Timbre speaks, Prisma listens, compare
    python scripts/gnani_smoke_test.py roundtrip --keyterms "Maggi,Amul butter"      # E4
    python scripts/gnani_smoke_test.py stt some.wav --language hi-IN
    python scripts/gnani_smoke_test.py concurrency --max 8                           # E5

Add --save to write the run to evaluation/results/ (the only place figures for the
README may come from). All speech here is synthetic: it is made by Timbre from the
sentences below, never recorded from a person.

The round trip is optimistic: synthetic speech is cleaner than a real caller.
"""

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# (label, tts language, text). The text is also the reference the transcript is scored against.
SENTENCES = [
    ("hindi", "hi-IN", "दो किलो आटा और एक लीटर तेल चाहिए"),
    ("telugu", "te-IN", "రెండు కిలోల బియ్యం మరియు ఒక లీటర్ నూనె కావాలి"),
    ("english", "en-IN", "I want two packets of Maggi and one Amul butter"),
    ("hinglish", "hi-en", "Do kilo atta aur one litre oil dena"),
    ("hindi_number", "hi-IN", "मेरा प्रोजेक्ट का खर्च डेढ़ लाख रुपये है"),
    ("english_number", "en-IN", "The total is two hundred and sixty rupees"),
]


def load_key():
    if os.environ.get("GNANI_API_KEY"):
        return
    try:
        import local_config
        key = getattr(local_config, "GNANI_API_KEY", "")
        if key and not key.startswith("your-"):
            os.environ["GNANI_API_KEY"] = key
    except ImportError:
        pass
    if not os.environ.get("GNANI_API_KEY"):
        sys.exit("GNANI_API_KEY is not set. Register at https://app.gnani.ai/voice, then put the key in "
                 "the environment or local_config.py.")


def words(text: str) -> list:
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def word_error_rate(reference: str, hypothesis: str) -> float:
    r, h = words(reference), words(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i]
        for j, hw in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw)))
        prev = cur
    return prev[-1] / len(r)


def write_wav(path: Path, pcm: bytes, rate=16000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def read_wav16k(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
            sys.exit("Need a 16 kHz mono 16-bit WAV.")
        return w.readframes(w.getnframes())


def synth(text: str, language: str):
    from dukaan_dost import tts_gnani
    stream = tts_gnani.start_streaming_synthesis(text, language)
    t0 = time.monotonic()
    pcm = b"".join(stream.chunks())
    total_ms = (time.monotonic() - t0) * 1000
    return pcm, stream.first_chunk_ms, total_ms, stream.failed, getattr(stream, "_error", None)


def listen(pcm: bytes, language: str | None, realtime=True):
    """Feeds pcm to Prisma at real-time pace. Returns (text, language, wait_ms) where wait_ms is
    the time from the last audio being handed over to the result coming back."""
    from dukaan_dost import stt_gnani
    session = stt_gnani.start_streaming_session(language)
    step = 1024
    t0 = time.monotonic()
    for i, off in enumerate(range(0, len(pcm), step)):
        session.feed(pcm[off:off + step])
        if realtime:
            time.sleep(max(0.0, t0 + (i + 1) * 0.032 - time.monotonic()))
    t_end = time.monotonic()
    text, lang = session.finish()
    return text, lang, (time.monotonic() - t_end) * 1000


def cmd_tts(args):
    out = Path(args.out)
    rows = []
    for label, lang, text in SENTENCES:
        pcm, first_ms, total_ms, failed, err = synth(text, lang)
        ok = bool(pcm) and not failed
        if ok:
            write_wav(out / f"{label}.wav", pcm)
        secs = len(pcm) / 2 / 16000
        rows.append({"label": label, "language": lang, "ok": ok, "first_chunk_ms": first_ms,
                     "total_ms": round(total_ms), "audio_seconds": round(secs, 2), "error": err})
        print(f"{label:15} {lang:6} first chunk {first_ms and round(first_ms)} ms, "
              f"total {round(total_ms)} ms, {secs:.1f} s of audio" + ("" if ok else f"  FAILED: {err}"))
    print(f"\nWAV files in {out}. Listen to the numbers: do they sound right in Hindi and Telugu?")
    return {"experiment": "E2 tts", "rows": rows}


def cmd_roundtrip(args):
    from dukaan_dost import stt_gnani
    if args.keyterms:
        print(f"keyterms: {stt_gnani.set_keyterms([t.strip() for t in args.keyterms.split(',')])} kept")
    rows = []
    for label, lang, text in SENTENCES:
        pcm, first_ms, _, failed, err = synth(text, lang)
        if failed or not pcm:
            print(f"{label:15} synthesis FAILED: {err}")
            rows.append({"label": label, "error": err})
            continue
        heard, heard_lang, wait_ms = listen(pcm, None if args.hints else lang if lang != "hi-en" else "hi-IN")
        wer = word_error_rate(text, heard)
        rows.append({"label": label, "reference": text, "heard": heard, "language": heard_lang,
                     "wer": round(wer, 3), "stt_wait_ms": round(wait_ms), "tts_first_chunk_ms": first_ms})
        print(f"{label:15} WER {wer:.2f}  wait after speech {round(wait_ms)} ms  lang={heard_lang}\n"
              f"{'':15} said : {text}\n{'':15} heard: {heard}")
    ok = [r["wer"] for r in rows if "wer" in r]
    if ok:
        print(f"\nmean WER over {len(ok)} sentences: {statistics.mean(ok):.2f} (synthetic speech; optimistic)")
    return {"experiment": "E3/E4/E6 roundtrip", "keyterms": args.keyterms or None, "rows": rows}


def cmd_stt(args):
    pcm = read_wav16k(args.wav)
    heard, lang, wait_ms = listen(pcm, args.language)
    print(f"heard: {heard!r}  lang={lang}  wait after speech {round(wait_ms)} ms")
    return {"experiment": "stt", "file": Path(args.wav).name, "heard": heard, "language": lang,
            "stt_wait_ms": round(wait_ms)}


def cmd_concurrency(args):
    """Opens sessions one by one and holds them open until one is refused (E5)."""
    from websockets.asyncio.client import connect
    from dukaan_dost import stt_gnani

    async def probe():
        held, refused = [], None
        try:
            for n in range(1, args.max + 1):
                try:
                    ws = await asyncio.wait_for(
                        connect(stt_gnani._url(), additional_headers=stt_gnani._build_headers("hi-IN")), 10)
                    first = await asyncio.wait_for(ws.recv(), 10)
                    msg = json.loads(first)
                    if msg.get("type") == "error":
                        refused = (n, msg.get("message"))
                        await ws.close()
                        break
                    held.append(ws)
                    print(f"session {n}: open")
                    await asyncio.sleep(0.4)           # the docs say very fast bursts can be rejected
                except Exception as e:
                    refused = (n, str(e))
                    break
        finally:
            for ws in held:
                await ws.close()
        return len(held), refused

    n, refused = asyncio.run(probe())
    print(f"\n{n} sessions held open at once." + (f" Session {refused[0]} was refused: {refused[1]}" if refused
                                                  else f" None refused up to --max {args.max}."))
    return {"experiment": "E5 concurrency", "held": n, "refused": refused, "max_tried": args.max}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tts"); t.add_argument("--out", default=str(ROOT / "evaluation" / "audio" / "smoke"))
    r = sub.add_parser("roundtrip"); r.add_argument("--keyterms", default="")
    r.add_argument("--hints", action="store_true", help="give Prisma the language hint list instead of the true language")
    s = sub.add_parser("stt"); s.add_argument("wav"); s.add_argument("--language", default=None)
    c = sub.add_parser("concurrency"); c.add_argument("--max", type=int, default=8)
    for p in (t, r, s, c):
        p.add_argument("--save", action="store_true", help="write the run to evaluation/results/")
    args = ap.parse_args()

    load_key()
    result = {"cmd": args.cmd, "when": datetime.now().astimezone().isoformat(timespec="seconds"),
              "synthetic_speech_only": True, **{"data": {"tts": cmd_tts, "roundtrip": cmd_roundtrip,
                                                         "stt": cmd_stt, "concurrency": cmd_concurrency}[args.cmd](args)}}
    if args.save:
        out = ROOT / "evaluation" / "results" / f"smoke_{args.cmd}_{datetime.now():%Y%m%d_%H%M%S}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
