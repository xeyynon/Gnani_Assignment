"""
Tests for the scripted caller (transport_replay.py), using a small stand-in for the agent: it listens to
the microphone, notices the end of speech, and replies after a short delay, like the real pipeline does.

    python -m pytest tests/test_transport_replay.py
"""

import io
import json
import struct
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaan_dost import transport, transport_replay  # noqa: E402
from dukaan_dost.transport_replay import ReplayTransport  # noqa: E402

FRAME = 960          # 30 ms at 16 kHz


def write_wav(path, seconds, freq=300, amp=8000):
    t = np.arange(int(16000 * seconds)) / 16000
    pcm = (amp * np.sin(2 * np.pi * freq * t)).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())
    return path


def wav_bytes(seconds):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return out.getvalue()


class FakeAgent(threading.Thread):
    """Greets when a call starts; after speech followed by `hangover` of quiet, replies after `think` seconds."""

    def __init__(self, t, hangover=0.4, think=0.2, reply_sec=0.6, greet_sec=0.3, interruptible=False, mute=False):
        super().__init__(daemon=True)
        self.t, self.hangover, self.think = t, hangover, think
        self.reply_sec, self.greet_sec, self.interruptible, self.mute = reply_sec, greet_sec, interruptible, mute
        self.stop = threading.Event()
        self.heard_frames = 0
        self.max_quiet_rms = 0.0
        self.turn = 0

    def run(self):
        last_key = None
        while not self.stop.is_set():
            key, _ = self.t.find_call()
            if key is None:
                last_key = None
                time.sleep(0.05)
                continue
            cap = self.t.open_capture(key)
            if key != last_key:
                last_key = key
                self.turn = 0
                threading.Thread(target=lambda: self.t.play(key, wav_bytes(self.greet_sec), 5), daemon=True).start()
            speaking, quiet_frames = False, 0
            while not self.stop.is_set() and self.t.find_call()[0] == key:
                frame = cap.read_frame(FRAME, 1.0)
                if len(frame) < FRAME:
                    continue
                rms = float(np.sqrt(np.mean(np.frombuffer(frame, dtype=np.int16).astype(np.float32) ** 2)))
                loud = rms > 2000
                if loud:
                    self.heard_frames += 1
                    speaking, quiet_frames = True, 0
                    if self.interruptible and self.t._playing:
                        self.t.stop_playback()
                else:
                    quiet_frames += 1
                    if not speaking:
                        self.max_quiet_rms = max(self.max_quiet_rms, rms)
                if speaking and quiet_frames * 0.03 >= self.hangover:
                    speaking = False
                    self.turn += 1
                    if self.mute:
                        continue
                    time.sleep(self.think)
                    self.t.send_event({"type": "user", "text": f"heard {self.turn}", "lang": "en-IN"})
                    self.t.send_event({"type": "agent", "reply": self.turn, "text": f"reply {self.turn}"})
                    threading.Thread(target=lambda k=key: self.t.play(k, wav_bytes(self.reply_sec), 5), daemon=True).start()


def make_plan(tmp_path, calls, **extra):
    plan = {"results": str(tmp_path / "results.json"), "min_turn_sec": 0, "quiet_sec": 0.5,
            "response_timeout_sec": 5, "calls": calls}
    plan.update(extra)
    return plan


def call(tmp_path, cid, n_turns=2, shop="dukaan_dost", seconds=0.5, **turn_extra):
    return {"id": cid, "shop": shop,
            "turns": [{"audio": str(write_wav(tmp_path / f"{cid}_{i}.wav", seconds)), "text": f"turn {i}", **turn_extra}
                      for i in range(n_turns)]}


def run_to_end(t, agent, limit=40):
    agent.start()
    t.start()
    deadline = time.monotonic() + limit
    while not t._done and time.monotonic() < deadline:
        time.sleep(0.1)
    agent.stop.set()
    t.close()
    assert t._done, "the scripted calls did not finish"


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(transport_replay, "END_CALL_WAIT_SEC", 3.0)


def test_a_scripted_call_runs_through_the_agent_and_is_measured(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 2)]))
    run_to_end(t, FakeAgent(t))
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert data["done"] is True and len(data["calls"]) == 1
    c = data["calls"][0]
    assert c["id"] == "c1" and c["shop"] == "dukaan_dost" and c["greeting_played"] is True
    assert [x["i"] for x in c["turns"]] == [0, 1]
    for turn in c["turns"]:
        # hangover 0.4 s + thinking 0.2 s after the caller's last sample, within a frame or two
        assert 450 <= turn["first_audio_after_ms"] <= 1100, turn
        assert turn["speech_seconds"] == 0.5 and "no_response" not in turn


def test_what_the_agent_heard_and_said_is_attributed_to_the_right_turn(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 2)]))
    run_to_end(t, FakeAgent(t))
    turns = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["calls"][0]["turns"]
    assert turns[0]["heard"] == ["heard 1"] and turns[0]["agent_said"] == ["reply 1"]
    assert turns[1]["heard"] == ["heard 2"] and turns[1]["agent_said"] == ["reply 2"]
    assert turns[0]["agent_played_seconds"] == 0.6


def test_the_microphone_runs_at_real_time_pace(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 1)]))
    t0 = time.monotonic()
    frames = 0
    cap = t.open_capture("k")
    while frames < 40:
        assert len(cap.read_frame(FRAME, 1.0)) == FRAME
        frames += 1
    elapsed = time.monotonic() - t0
    assert 1.1 <= elapsed <= 1.6               # 40 frames of 30 ms = 1.2 s, not instant


def test_a_stalled_microphone_returns_nothing_instead_of_blocking(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, []))
    t._due = time.monotonic() + 5
    t0 = time.monotonic()
    assert t._next_frame(FRAME, 0.2) == b""
    assert time.monotonic() - t0 < 0.5


def test_silence_between_the_turns_is_digital_silence_without_noise(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 1)]))
    agent = FakeAgent(t)
    run_to_end(t, agent)
    assert agent.max_quiet_rms == 0.0


def test_steady_noise_is_mixed_into_the_microphone_all_through_the_call(tmp_path):
    noise = tmp_path / "noise.wav"
    write_wav(noise, 1.0, freq=120, amp=10000)
    plan = make_plan(tmp_path, [call(tmp_path, "c1", 1)], noise={"path": str(noise), "gain": 0.1})
    t = ReplayTransport(plan)
    agent = FakeAgent(t)
    run_to_end(t, agent)
    assert 300 < agent.max_quiet_rms < 1000          # 0.1 x amplitude 10000 / sqrt(2), about 700: audible but below speech


def test_the_agent_hears_the_scripted_speech(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 2, seconds=0.6)]))
    agent = FakeAgent(t)
    run_to_end(t, agent)
    assert 2 * 0.6 / 0.03 * 0.8 <= agent.heard_frames <= 2 * 0.6 / 0.03 * 1.2     # about 40 loud frames in all


def test_a_turn_the_agent_never_answers_is_marked_and_does_not_hang(tmp_path):
    plan = make_plan(tmp_path, [call(tmp_path, "c1", 1)], response_timeout_sec=1.5)
    t = ReplayTransport(plan)
    run_to_end(t, FakeAgent(t, mute=True))
    turn = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["calls"][0]["turns"][0]
    assert turn["no_response"] is True and turn["first_audio_after_ms"] is None


def test_calls_run_one_after_another_each_with_its_own_key_and_shop(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "a", 1, shop="shop_a"), call(tmp_path, "b", 1, shop="shop_b")]))
    keys, shops = [], []

    class Watcher(FakeAgent):
        def run(self):
            threading.Thread(target=self._watch, daemon=True).start()
            super().run()

        def _watch(self):
            while not self.stop.is_set():
                k = self.t.find_call()[0]
                if k and (not keys or keys[-1] != k):
                    keys.append(k)
                    shops.append(self.t.call_shop())
                time.sleep(0.05)

    run_to_end(t, Watcher(t))
    assert keys == ["replay-a", "replay-b"] and shops == ["shop_a", "shop_b"]
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in data["calls"]] == ["a", "b"] and data["calls"][0]["end_iso"] <= data["calls"][1]["begin_iso"]


def test_no_call_is_up_before_and_after_the_script(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 1)]))
    assert t.find_call() == (None, None) and t.call_shop() is None and t.live_calls() == []
    run_to_end(t, FakeAgent(t))
    assert t.find_call() == (None, None)


def test_a_turn_can_interrupt_the_agent_while_it_is_still_speaking(tmp_path):
    first = call(tmp_path, "c1", 2, seconds=0.5)
    first["turns"][1]["barge_in_after_sec"] = 0.3
    t = ReplayTransport(make_plan(tmp_path, [first]))
    agent = FakeAgent(t, reply_sec=2.0, interruptible=True)
    run_to_end(t, agent)
    c = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["calls"][0]
    assert c["interrupted_clips"] >= 1


def test_playing_a_clip_takes_its_real_duration_and_can_be_stopped(tmp_path):
    t = ReplayTransport(make_plan(tmp_path, []))
    t0 = time.monotonic()
    t.play("k", wav_bytes(0.4), 5)
    assert 0.35 <= time.monotonic() - t0 <= 0.7
    threading.Timer(0.1, t.stop_playback).start()
    t0 = time.monotonic()
    t.play("k", wav_bytes(3.0), 5)
    assert time.monotonic() - t0 < 1.0 and t._plays[-1]["stopped"] is True
    assert t.stop_playback() is False                    # nothing playing now


def test_audio_in_the_wrong_format_is_refused_and_the_run_still_ends(tmp_path):
    bad = tmp_path / "bad.wav"
    with wave.open(str(bad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(struct.pack("<h", 0) * 800)
    plan = make_plan(tmp_path, [{"id": "x", "shop": "s", "turns": [{"audio": str(bad)}]}])
    t = ReplayTransport(plan)
    run_to_end(t, FakeAgent(t))
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["done"] is True


def test_the_factory_builds_it_from_the_environment(tmp_path, monkeypatch):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(make_plan(tmp_path, [])), encoding="utf-8")
    monkeypatch.setenv("REPLAY_PLAN", str(plan))
    assert isinstance(transport.create("replay"), ReplayTransport)
    monkeypatch.delenv("REPLAY_PLAN")
    with pytest.raises(ValueError, match="REPLAY_PLAN"):
        transport.create("replay")


def test_every_hook_the_main_program_calls_on_a_transport_exists_on_the_replay_transport(tmp_path):
    """Regression: the admin page added add_ws_handler(), and the replay transport crashed at startup without it."""
    import re
    t = ReplayTransport(make_plan(tmp_path, []))
    source = (Path(__file__).resolve().parent.parent / "dukaan_dost" / "app.py").read_text(encoding="utf-8")
    called = set(re.findall(r"_transport\.([a-z_]+)\(", source))
    missing = sorted(name for name in called if not hasattr(t, name))
    assert missing == [], missing
    t.add_ws_handler("/x", lambda ws: None)              # accepted and ignored


# ---- measurement fixes (B-56, B-57, B-63) ---------------------------------------------------------

def write_wav_with_tail(path, speech_sec, tail_sec, amp=8000):
    t = np.arange(int(16000 * speech_sec)) / 16000
    pcm = np.concatenate([(amp * np.sin(2 * np.pi * 300 * t)).astype(np.int16), np.zeros(int(16000 * tail_sec), dtype=np.int16)])
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())
    return path


def test_trailing_silence_is_counted_in_whole_20_ms_frames_from_the_end():
    loud = (8000 * np.sin(np.arange(8000) / 7)).astype(np.int16)
    clip = np.concatenate([loud, np.zeros(4800, dtype=np.int16)]).tobytes()          # 0.3 s of quiet at the end
    assert transport_replay.trailing_silence_ms(clip) == 300
    assert transport_replay.trailing_silence_ms(loud.tobytes()) == 0
    assert transport_replay.trailing_silence_ms(b"") == 0
    quiet_noise = np.concatenate([loud, (100 * np.sin(np.arange(3200))).astype(np.int16)]).tobytes()   # hiss under RMS 300 counts as quiet
    assert transport_replay.trailing_silence_ms(quiet_noise) == 200


def test_each_turn_records_the_silence_at_the_end_of_its_clip(tmp_path):
    c = {"id": "c1", "shop": "s", "turns": [{"audio": str(write_wav_with_tail(tmp_path / "a.wav", 0.5, 0.3)), "text": "x"}]}
    t = ReplayTransport(make_plan(tmp_path, [c]))
    run_to_end(t, FakeAgent(t))
    turn = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["calls"][0]["turns"][0]
    assert 280 <= turn["trailing_silence_ms"] <= 300 and turn["speech_seconds"] == 0.8


def test_a_barge_in_still_lands_on_the_reply_when_min_turn_sec_is_longer_than_the_reply(tmp_path):
    """Regression (B-56): the min-turn gap used to run first, the reply ended, and the turn was injected into silence."""
    first = call(tmp_path, "c1", 2, seconds=0.5)
    first["turns"][1]["barge_in_after_sec"] = 0.3
    t = ReplayTransport(make_plan(tmp_path, [first], min_turn_sec=6))
    run_to_end(t, FakeAgent(t, reply_sec=2.0, interruptible=True), limit=60)
    c = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["calls"][0]
    assert c["interrupted_clips"] >= 1
    assert c["turns"][1]["t_start"] - c["turns"][0]["t_start"] < 6        # it did not wait out the 6 s gap


def test_a_results_write_that_fails_at_first_is_retried(tmp_path, monkeypatch):
    """Regression (B-63): on Windows os.replace fails while the runner is reading the file."""
    t = ReplayTransport(make_plan(tmp_path, []))
    real, fails = transport_replay.os.replace, {"n": 0}

    def flaky(a, b):
        fails["n"] += 1
        if fails["n"] <= 3:
            raise PermissionError("in use")
        return real(a, b)

    monkeypatch.setattr(transport_replay.os, "replace", flaky)
    assert t._write_results() is True and fails["n"] == 4
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["done"] is False


def test_a_results_write_that_keeps_failing_never_marks_the_run_done(tmp_path, monkeypatch):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "c1", 1)]))
    t._write_results()                                                  # a good file with done false exists
    t._done = True
    monkeypatch.setattr(transport_replay.os, "replace", lambda a, b: (_ for _ in ()).throw(PermissionError("in use")))
    assert t._write_results() is False                                  # no exception either
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["done"] is False


def test_one_failed_write_between_calls_does_not_abort_the_remaining_calls(tmp_path, monkeypatch):
    t = ReplayTransport(make_plan(tmp_path, [call(tmp_path, "a", 1), call(tmp_path, "b", 1)]))
    real, state = transport_replay.os.replace, {"n": 0}

    def flaky(a, b):
        state["n"] += 1
        if state["n"] <= 6:                       # the first write (after call a) fails all 6 tries
            raise PermissionError("in use")
        return real(a, b)

    monkeypatch.setattr(transport_replay.os, "replace", flaky)
    run_to_end(t, FakeAgent(t))
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert data["done"] is True and [c["id"] for c in data["calls"]] == ["a", "b"]
