"""
profile_frame_cost.py — how much CPU the per-frame audio work uses.

Run it from the project root, on the machine that will run the demo:

    python -m evaluation.profile_frame_cost

It times the functions the recorder runs on audio and prints each as a share of
the frame's duration (30 ms of audio must be handled in well under 30 ms of
CPU). This is the evidence for any decision to compile a hot path with Cython: if a function isn't a visible share of the frame,
compiling it can't make a call feel faster.

It measures CPU work only. The things that make a reply slow (the speech,
language-model and text-to-speech network calls, and the end-of-speech wait)
are not CPU-bound; time those with the [SPAN] lines in dukaan_dost.log.
"""

import os
import sys
import timeit
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SHOP_NAME", "profile")   # importing the app needs no real shop

import dukaan_dost.app as app  # noqa: E402


def _time_ms(fn, number: int) -> float:
    """Best of five runs, in milliseconds per call."""
    return min(timeit.repeat(fn, number=number, repeat=5)) / number * 1000


def main() -> None:
    rng = np.random.default_rng(0)
    n = app.FRAME_BYTES // 2
    t = np.arange(n) / app.SAMPLE_RATE
    speech = (3000 * np.sin(2 * np.pi * 140 * t) + 800 * rng.standard_normal(n)).astype("<i2").tobytes()
    utterance = speech * 10   # ~300 ms, what _learn_caller_pitch sees

    per_frame = [
        ("_energy", lambda: app._energy(speech), 2000),
        ("_is_speech (webrtcvad)", lambda: app._is_speech(speech), 2000),
        ("_is_speech_strict (webrtcvad)", lambda: app._is_speech_strict(speech), 2000),
        ("_estimate_pitch_hz", lambda: app._estimate_pitch_hz(speech), 300),
    ]
    per_utterance = [
        ("_learn_caller_pitch (300 ms)", lambda: app._learn_caller_pitch(utterance), 100),
    ]
    frame_ms = app.VAD_FRAME_MS

    print(f"Frame = {frame_ms} ms of audio at {app.SAMPLE_RATE} Hz\n")
    print(f"{'function':<34}{'ms/call':>10}{'% of frame':>13}")
    always = 0.0
    for name, fn, number in per_frame:
        ms = _time_ms(fn, number)
        if name in ("_energy", "_is_speech (webrtcvad)", "_is_speech_strict (webrtcvad)"):
            always += ms   # run on every frame; the pitch estimate runs only on some
        print(f"{name:<34}{ms:>10.4f}{ms / frame_ms * 100:>12.2f}%")
    print("\nOnce per utterance:")
    for name, fn, number in per_utterance:
        ms = _time_ms(fn, number)
        print(f"{name:<34}{ms:>10.4f}{ms / frame_ms * 100:>12.2f}%  (of one frame)")
    print(f"\nWork on EVERY frame (energy + both VAD checks): {always:.4f} ms "
          f"= {always / frame_ms * 100:.2f}% of the frame")


if __name__ == "__main__":
    main()
