"""
Regression tests for the call-lifecycle bugs found in app.py and conversation_manager.py (B-64, B-65, B-67, B-69)
and two small ones: a clip that timed out must not count as heard, and "repeat" right after the greeting.

They drive the real processor, watchdog and playback threads with the model and the speech synthesis replaced.

    python -m pytest tests/test_lifecycle_fixes.py
"""

import logging
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dukaan_dost import store  # noqa: E402
from dukaan_dost import stock as stock_mod  # noqa: E402


@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


class Rig:
    """A running processor thread with the model and the speech synthesis replaced."""

    def __init__(self, app, monkeypatch):
        self.app = app
        self.mp = monkeypatch
        self.said = []              # (text, language) of everything handed to the speech synthesiser
        self.model_calls = []       # transcripts that reached the model
        self.recorded = []          # (transcript, reply text) of every turn the processor finished
        self.tts_ok = lambda text: True
        self.reply = lambda transcript: ["Noted that.", "Anything else?"]
        self.thread = None
        monkeypatch.setattr(app._transport, "send_event", lambda e: None)
        monkeypatch.setattr(app, "_record_turn", lambda gen, pcm, t, lang, reply: self.recorded.append((t, reply)))
        monkeypatch.setattr(app, "_tts_and_enqueue", self._tts)
        monkeypatch.setattr(app, "_ask_streaming", self._model)

    def _tts(self, text, language, gen, reply_id):
        self.said.append((text, language))
        if not self.tts_ok(text):
            return [], None
        return [b"wav:" + text.encode("utf-8")], 1.0

    def _model(self, transcript, language):
        self.model_calls.append(transcript)
        for sentence in self.reply(transcript):
            yield sentence, language

    def new_call(self):
        a = self.app
        a._clear_history("new call")
        a._drain_queues("new call")
        a._set_active_shop()

    def hang_up_and_redial(self):
        a = self.app
        a._clear_history("call ended")
        a._drain_queues("call ended")
        self.new_call()

    def start(self):
        a = self.app
        a._shutdown.clear()
        self.thread = threading.Thread(target=a.processor_thread, daemon=True)
        self.thread.start()

    def say(self, transcript, language="en-IN", gen=None):
        a = self.app
        a.audio_q.put((a._call_gen if gen is None else gen, b"", 3.0, {}, False, transcript, language, 0))

    def settle(self, timeout=5.0):
        """Wait until the processor has finished everything queued so far (it handles items in order)."""
        a = self.app
        a.audio_q.put((a._call_gen, b"", 3.0, {}, False, "ok ok", "en-IN", 0))
        deadline = time.time() + timeout
        n = len(self.recorded)
        while time.time() < deadline:
            if any(t == "ok ok" for t, _ in self.recorded[n:]):
                return
            time.sleep(0.02)
        raise AssertionError("the processor did not finish in time")

    def stop(self):
        self.app._shutdown.set()
        self.app.audio_q.put((-1, b"", 0.0, {}, False, "", "en-IN", 0))      # wakes the processor from its wait
        if self.thread:
            self.thread.join(timeout=3)
        self.app._shutdown.clear()


@pytest.fixture
def rig(app, monkeypatch, tmp_path):
    monkeypatch.setattr(store, "ORDERS_DIR", tmp_path)
    monkeypatch.setattr(app._transport, "call_shop", lambda: "dukaan_dost")
    app._finish_order("test setup")
    app._clear_history("test setup")
    while not app.reply_q.empty():
        app.reply_q.get_nowait()
    r = Rig(app, monkeypatch)
    r.new_call()
    yield r
    r.stop()
    app._finish_order("test teardown")
    app._clear_history("test teardown")


# ---- B-64: a turn still running at hang-up must not leak into the next call ----------------------------------------

def test_clearing_the_history_moves_the_generation_on_first(app):
    before = app._call_gen
    app._clear_history("call ended")
    assert app._call_gen > before


def test_the_recorders_new_node_reset_does_not_move_the_generation_or_drop_the_greeting(app):
    """B-86: the order is call detected -> reset ("new call") -> drain -> greeting queued -> the recorder resets again
    ("new node ..."). That last reset must not move the generation, or the greeting is discarded as stale, the
    greeting guard never clears and the recorder stays deaf for the whole call (every call after the first)."""
    app._clear_history("new call")
    app._drain_queues("new call")
    greeting_gen = app._call_gen
    app.reply_q.put((greeting_gen, b"greeting", 1, False))
    app._clear_history("new node replay-h02")
    assert app._call_gen == greeting_gen
    gen, wav, _, _ = app.reply_q.get_nowait()
    assert gen == app._call_gen                                   # the greeting is still current when the playback thread sees it


@pytest.mark.parametrize("reason", ["call ended", "call ended (node changed)", "new call"])
def test_the_boundaries_the_watchdog_handles_do_move_the_generation(app, reason):
    before = app._call_gen
    app._clear_history(reason)
    assert app._call_gen > before


@pytest.mark.parametrize("reason", ["new node abc", "", "test", "barge-in"])
def test_other_resets_leave_the_generation_alone(app, reason):
    before = app._call_gen
    app._clear_history(reason)
    assert app._call_gen == before


def test_a_turn_that_finishes_after_hang_up_leaves_the_next_call_clean(app, rig):
    release = threading.Event()
    entered = threading.Event()

    def slow_model(transcript, language):
        entered.set()
        release.wait(5)
        yield "Caller A's answer.", language

    rig.mp.setattr(app, "_ask_streaming", slow_model)
    rig.start()
    rig.say("caller A wants two kilo sugar please")
    assert entered.wait(3)                          # the turn is in the model
    rig.hang_up_and_redial()                        # caller A hangs up, caller B calls
    release.set()
    rig.settle()
    assert app._history == []                       # B starts with an empty history, so the model greets B
    assert app._last_reply_wav is None and app._last_reply_lang is None


def test_repeat_in_the_new_call_does_not_replay_the_old_callers_audio(app, rig):
    release = threading.Event()
    entered = threading.Event()

    def slow_model(transcript, language):
        entered.set()
        release.wait(5)
        yield "Caller A's answer.", language

    rig.mp.setattr(app, "_ask_streaming", slow_model)
    rig.start()
    rig.say("caller A wants two kilo sugar please")
    assert entered.wait(3)
    rig.hang_up_and_redial()
    release.set()
    rig.settle()
    rig.say("repeat please")
    rig.settle()
    assert app.reply_q.empty()                      # nothing of caller A is replayed to caller B


# ---- B-65: nothing is recorded as said when no audio was made ---------------------------------------------------------

def test_a_reply_with_no_audio_stays_out_of_the_history_and_is_apologised_for(app, rig):
    fallback = app._get_conv_mgr()._fallback_for("en-IN")
    rig.tts_ok = lambda text: text == fallback      # synthesis fails for the answer, works for the apology
    app._last_reply_wav = b"previous turn"
    app._last_reply_lang = "en-in"
    rig.start()
    rig.say("two kilo sugar please")
    rig.settle()
    assert app._history == []
    assert app._last_reply_wav == b"previous turn"  # "repeat" must not be pointed at a sentence nobody heard
    assert rig.said[-1] == (fallback, "en-IN")      # the caller is told something went wrong


def test_when_the_apology_also_fails_the_turn_is_only_logged(app, rig, caplog):
    rig.tts_ok = lambda text: False
    rig.start()
    with caplog.at_level(logging.ERROR):
        rig.say("one kilo sugar please")
        rig.settle()
    assert app._history == []
    assert any("No audio" in r.getMessage() for r in caplog.records)


def test_only_the_sentences_that_were_spoken_are_recorded(app, rig):
    rig.tts_ok = lambda text: text != "Anything else?"
    rig.start()
    rig.say("one kilo sugar please")
    rig.settle()
    assert [h["content"] for h in app._history] == ["one kilo sugar please", "Noted that."]


# ---- B-67: a broken shop must not stop its calls --------------------------------------------------------------------------

def test_a_stock_list_of_the_wrong_shape_does_not_stop_product_name_boosting(app, monkeypatch):
    def boom(shop_dir):
        raise AttributeError("'str' object has no attribute 'get'")
    monkeypatch.setattr(stock_mod, "load", boom)
    app._boost_product_names("dukaan_dost")         # must not raise


def test_the_conversation_manager_survives_a_stock_list_of_the_wrong_shape(monkeypatch):
    from dukaan_dost.conversation_manager import ConversationManager
    from dukaan_dost import shops

    def boom(shop_dir):
        raise TypeError("string indices must be integers")
    monkeypatch.setattr(stock_mod, "load", boom)
    mgr = ConversationManager(shops.shop_dir("dukaan_dost"), "gemini-2.5-flash", 100, 0.5)
    assert mgr.stock_items == [] and mgr.names_product("sugar") is False


def test_a_call_to_a_shop_with_a_bad_stock_list_still_gets_its_greeting(app, rig, monkeypatch):
    def boom(shop_dir):
        raise AttributeError("bad stock")
    monkeypatch.setattr(stock_mod, "load", boom)
    greeted = []
    monkeypatch.setattr(app, "_play_greeting", lambda: greeted.append(app._call_gen))
    monkeypatch.setattr(app, "_find_call", lambda: ("in1", "out1"))
    monkeypatch.setattr(app, "WATCHDOG_SEC", 0.05)
    monkeypatch.setattr(app, "_capture_key", None)
    monkeypatch.setattr(app, "_playback_key", None)
    start_gen = app._call_gen
    app._shutdown.clear()
    t = threading.Thread(target=app.watchdog_thread, daemon=True)
    t.start()
    time.sleep(0.6)
    app._shutdown.set()
    t.join(timeout=3)
    app._shutdown.clear()
    assert len(greeted) == 1                        # once, not zero and not once per poll
    assert app._call_gen - start_gen <= 6           # the call was detected once (a few bumps), not on every poll


def _broken_shop(tmp_path, monkeypatch, app):
    shop = tmp_path / "shops" / "brokenshop"
    shop.mkdir(parents=True)
    (shop / "config.yaml").write_text("system_prompt: [unclosed\n", encoding="utf-8")
    monkeypatch.setattr(app._shops, "SHOPS_DIR", tmp_path / "shops")
    monkeypatch.setattr(app._transport, "call_shop", lambda: "brokenshop")


def test_a_shop_that_cannot_be_loaded_answers_with_the_built_in_sentence(app, rig, monkeypatch, tmp_path, caplog):
    _broken_shop(tmp_path, monkeypatch, app)
    with caplog.at_level(logging.INFO):
        rig.new_call()
        rig.start()
        rig.say("two kilo sugar please")
        rig.say("and one packet salt")
        rig.settle()
    assert rig.said.count((app.BUILTIN_FALLBACK["en-in"], "en-IN")) == 2
    assert rig.model_calls == []
    causes = [r for r in caplog.records if "cannot be loaded" in r.getMessage()]
    assert len(causes) == 1                         # the cause is logged once for the call, not once per turn
    assert app._history == []


def test_the_built_in_sentence_follows_the_callers_language(app):
    assert app._builtin_fallback("hi-IN") == app.BUILTIN_FALLBACK["hi-in"]
    assert app._builtin_fallback("te-in") == app.BUILTIN_FALLBACK["te-in"]
    assert app._builtin_fallback("xx") == app.BUILTIN_FALLBACK["en-in"]


# ---- B-69: repeat words must not swallow order turns --------------------------------------------------------------------------

ORDER_TURNS_WITH_A_REPEAT_WORD = [
    "add one kilo sugar again",
    "ek kilo chini dobara",
    "phir se do packet maggi",
    "one more time two packets maggi",
    "I want atta once more",
]


@pytest.mark.parametrize("transcript", ORDER_TURNS_WITH_A_REPEAT_WORD)
def test_an_order_turn_with_a_repeat_word_goes_to_the_order_flow(app, rig, transcript):
    app._set_active_shop()
    assert app._order is not None
    app._last_reply_wav = b"old reply"
    app._last_reply_lang = "en-in"
    rig.start()
    rig.say(transcript)
    rig.settle()
    assert rig.model_calls == [transcript]
    assert app.reply_q.empty()                      # the last reply was not replayed instead


def test_a_plain_repeat_request_still_replays_while_an_order_is_active(app, rig):
    app._set_active_shop()
    app._last_reply_wav = b"old reply"
    app._last_reply_lang = "en-in"
    rig.start()
    rig.say("sorry, please repeat that")
    rig.settle()
    assert rig.model_calls == []
    gen, wav, _rid, _cont = app.reply_q.get_nowait()
    assert wav == b"old reply"


def _order_with_sugar(app):
    app._set_active_shop()
    app._order.apply([{"op": "add", "sku": "SUGAR-1KG", "qty": 2}])


@pytest.mark.parametrize("transcript,language,expected_language", [
    ("repeat my order", "en-IN", "en-IN"),
    ("can you read my order", "en-IN", "en-IN"),
    ("mera order dobara bolo", "hi-IN", "hi-IN"),
    ("मेरा ऑर्डर दोबारा बताओ", "hi-IN", "hi-IN"),
    ("naa order malli cheppandi", "te-IN", "te-IN"),
    ("నా ఆర్డర్ మళ్ళీ చెప్పండి", "te-IN", "te-IN"),
])
def test_repeat_my_order_is_read_back_by_the_code(app, rig, transcript, language, expected_language):
    _order_with_sugar(app)
    app._last_reply_wav = b"Anything else?"
    app._last_reply_lang = "en-in"
    rig.start()
    rig.say(transcript, language)
    rig.settle()
    assert rig.model_calls == []
    assert rig.said == [(app._order.readback(expected_language), expected_language)]
    assert str(app._order.total()) in rig.said[0][0]
    assert app._history == []


def test_repeat_my_order_with_an_empty_order_keeps_the_old_behaviour(app, rig):
    app._set_active_shop()
    rig.start()
    rig.say("repeat my order")
    rig.settle()
    assert rig.model_calls == [] and rig.said == []         # nothing to repeat yet


def test_repeat_that_in_another_language_reads_the_order_from_code(app, rig, monkeypatch):
    _order_with_sugar(app)
    real = app._get_conv_mgr()
    monkeypatch.setattr(app, "_get_conv_mgr", lambda shop=None: real)
    monkeypatch.setattr(real, "handle_turn", lambda *a, **k: (_ for _ in ()).throw(AssertionError("model asked")))
    app._history.extend([{"role": "user", "content": "2 kilo sugar"},
                         {"role": "assistant", "content": "Added 2 kilo sugar, total 88 rupees. Anything else?"}])
    app._last_reply_wav = b"old"
    app._last_reply_lang = "en-in"
    rig.start()
    rig.say("please repeat that in hindi")
    rig.settle()
    assert rig.said == [(app._order.readback("hi-in"), "hi-in")]
    assert len(app._history) == 2                   # no fake user turn added


def test_the_synthetic_translate_instruction_never_enters_the_history(app, rig, monkeypatch):
    app._set_active_shop()
    app._order = None                               # no order: the old model path stays
    seen = []

    class Fake:
        stock_items = []

        def _fallback_for(self, language):
            return "Sorry."

        def names_product(self, text):
            return False

        def handle_turn(self, transcript, recent, context, language):
            seen.append(transcript)
            return "Hindi mein jawab.", language

    monkeypatch.setattr(app, "_get_conv_mgr", lambda shop=None: Fake())
    app._history.extend([{"role": "user", "content": "what time do you open"},
                         {"role": "assistant", "content": "We open at nine."}])
    app._last_reply_wav = b"old"
    app._last_reply_lang = "en-in"
    rig.start()
    rig.say("repeat that in hindi")
    rig.settle()
    assert seen and "previous answer" in seen[0]    # the model was asked...
    assert [h["content"] for h in app._history] == ["what time do you open", "We open at nine."]    # ...but it is not remembered


# ---- small ones ---------------------------------------------------------------------------------------------------------------

def test_play_says_false_when_the_clip_timed_out(app, monkeypatch):
    def timeout(node, wav, limit):
        raise app._transport_mod.PlaybackTimeout("no confirmation")
    monkeypatch.setattr(app, "_playback_key", "out1")
    monkeypatch.setattr(app._transport, "play", timeout)
    assert app._play(b"WAV", set_playing=False, echo_tail=False) is False
    monkeypatch.setattr(app._transport, "play", lambda node, wav, limit: None)
    assert app._play(b"WAV", set_playing=False, echo_tail=False) is True


@pytest.mark.parametrize("played,heard", [(True, "Hello there."), (False, "")])
def test_a_clip_that_did_not_play_to_the_end_is_not_counted_as_heard(app, rig, monkeypatch, played, heard):
    for name in ("ECHO_TAIL_SEC", "BARGE_IN_LISTEN_SEC", "TTS_CONTINUATION_WAIT_SEC"):
        monkeypatch.setattr(app, name, 0.01)
    done = threading.Event()

    def fake_play(wav, set_playing=True, echo_tail=True):
        done.set()
        return played

    monkeypatch.setattr(app, "_play", fake_play)
    rid = app._next_reply_id()
    app._spoken.planned(rid, "Hello there.", 1)
    app.reply_q.put((app._call_gen, b"wav", rid, False))
    app._shutdown.clear()
    t = threading.Thread(target=app.playback_thread, daemon=True)
    t.start()
    assert done.wait(3)
    time.sleep(0.3)
    app._shutdown.set()
    t.join(timeout=3)
    app._shutdown.clear()
    assert app._spoken.heard_text(rid) == heard


def test_repeat_right_after_the_greeting_replays_the_greeting(app, rig, monkeypatch):
    monkeypatch.setattr(app, "GREETING_DELAY_SEC", 0.0)
    app._set_active_shop()
    app._play_greeting()
    deadline = time.time() + 3
    while time.time() < deadline and not rig.said:
        time.sleep(0.02)
    time.sleep(0.1)
    greeting = rig.said[0][0]
    while not app.reply_q.empty():
        app.reply_q.get_nowait()
    rig.start()
    rig.say("repeat please")
    rig.settle()
    gen, wav, _rid, _cont = app.reply_q.get_nowait()
    assert wav == b"wav:" + greeting.encode("utf-8")


# ---- a call where nothing was ordered still shows up (the dashboard was empty after the first phone call) ----------

def test_a_call_with_no_order_still_leaves_a_call_record(app, rig, tmp_path):
    rig.start()
    app._clear_history("new node phone-ab12cd34")
    rig.say("What is this service called?")
    rig.settle()
    app._finish_order("call ended")
    snap = store.snapshot("dukaan_dost", root=tmp_path)
    assert snap["orders"] == []
    assert snap["summary"]["calls_total"] == 1
    call = snap["calls"][0]
    assert call["outcome"] == "nothing" and call["channel"] == "phone" and call["turns"] >= 1


def test_ending_the_same_call_twice_saves_one_record(app, rig, tmp_path):
    app._finish_order("call ended")
    app._finish_order("call ended")
    assert store.snapshot("dukaan_dost", root=tmp_path)["summary"]["calls_total"] == 1


def test_a_failed_call_record_never_breaks_the_hang_up(app, rig, monkeypatch):
    monkeypatch.setattr(app._store, "write_call", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    app._finish_order("call ended")                               # must not raise


# ---- a turn that came back empty is heard again with the language named ------------------------------------------

class FakeSession:
    def __init__(self, language, answers, log):
        self.language, self.answers, self.log, self.fed = language, answers, log, 0
        log.append(language)

    def feed(self, chunk):
        self.fed += len(chunk)

    def finish(self):
        return self.answers.get(self.language, ("", ""))


def _empty_turn(app, seconds=2.0, tentative=False):
    pcm = b"\x01\x02" * int(16000 * seconds)
    app.audio_q.put((app._call_gen, pcm, seconds, {}, tentative, "", "", 0))


def test_an_empty_turn_is_heard_again_in_the_calls_language(app, rig, monkeypatch):
    tried = []
    monkeypatch.setattr(app, "STT_LANGUAGE_RETRY", True)
    monkeypatch.setattr(app, "_locked_language_code", "te-IN")
    monkeypatch.setattr(app, "_start_streaming_session",
                        lambda lang, stale=None: FakeSession(lang, {"te-IN": ("అంతే.", "te-IN")}, tried))
    rig.start()
    _empty_turn(app)
    rig.settle()
    assert tried == ["te-IN"]                              # the call's language first, and it was enough
    assert rig.model_calls == ["అంతే."]


def test_with_no_language_known_yet_hindi_is_tried_and_then_telugu(app, rig, monkeypatch):
    tried = []
    monkeypatch.setattr(app, "STT_LANGUAGE_RETRY", True)
    monkeypatch.setattr(app, "_locked_language_code", None)
    monkeypatch.setattr(app, "_start_streaming_session",
                        lambda lang, stale=None: FakeSession(lang, {"te-IN": ("క్యాష్", "te-IN")}, tried))
    rig.start()
    _empty_turn(app)
    rig.settle()
    assert tried == ["hi-IN", "te-IN"] and rig.model_calls == ["క్యాష్"]


def test_the_retry_does_not_run_for_a_clip_that_is_too_short_or_not_confirmed_speech(app, rig, monkeypatch):
    tried = []
    monkeypatch.setattr(app, "STT_LANGUAGE_RETRY", True)
    monkeypatch.setattr(app, "_start_streaming_session",
                        lambda lang, stale=None: FakeSession(lang, {"hi-IN": ("बस", "hi-IN")}, tried))
    rig.start()
    _empty_turn(app, seconds=0.2)
    _empty_turn(app, seconds=2.0, tentative=True)
    rig.settle()
    assert tried == [] and rig.model_calls == []


def test_the_retry_can_be_switched_off_and_a_failing_retry_does_not_break_the_turn(app, rig, monkeypatch):
    tried = []
    monkeypatch.setattr(app, "STT_LANGUAGE_RETRY", False)
    monkeypatch.setattr(app, "_start_streaming_session", lambda lang, stale=None: FakeSession(lang, {}, tried))
    rig.start()
    _empty_turn(app)
    rig.settle()
    assert tried == []
    monkeypatch.setattr(app, "STT_LANGUAGE_RETRY", True)

    def boom(lang, stale=None):
        raise OSError("no network")
    monkeypatch.setattr(app, "_start_streaming_session", boom)
    _empty_turn(app)
    rig.settle()                                           # the turn ends with the usual apology, nothing raised
    assert rig.model_calls == []


def test_hindi_and_telugu_calls_name_their_language_to_the_recogniser_but_english_ones_do_not(app, monkeypatch):
    monkeypatch.setattr(app, "STT_USE_CALL_LANGUAGE", True)
    for locked, expected in (("te-IN", "te-IN"), ("hi-IN", "hi-IN"), ("en-IN", None), (None, None), ("", None)):
        monkeypatch.setattr(app, "_locked_language_code", locked)
        assert app._stt_language_for_call() == expected
    monkeypatch.setattr(app, "STT_USE_CALL_LANGUAGE", False)
    monkeypatch.setattr(app, "_locked_language_code", "te-IN")
    assert app._stt_language_for_call() is None
