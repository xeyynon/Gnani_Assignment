"""
conversation_manager.py

Orchestrates one reply turn:
  1. Load the always-on core knowledge (identity, language rules, bot
     rules, escalation triggers) — every turn, unconditionally.
  2. Retrieve the top-matching knowledge sections for the transcript
     via knowledge_retriever.get_relevant_context().
  3. Assemble ONE system prompt and make ONE call to Gemini.
  4. Run the reply through validator.validate_reply().

handle_turn()           — blocking, returns full reply (repeat/translate)
handle_turn_streaming() — yields sentence-sized chunks as Gemini streams
"""

import logging
import os
import re

import yaml

from .knowledge_retriever import get_core_context, get_relevant_context_maybe_cached
from .llm_gemini import ask as gemini_ask, stream as gemini_stream
from .validator import validate_reply

log = logging.getLogger("conversation_manager")

# Where a streamed reply is cut into speakable sentences. A full stop is NOT a
# sentence end after an abbreviation: "Rs. 260 hai" must stay one clip, because
# each clip is spoken separately with a listening pause between them, and a
# price split from its currency word is heard as a stumble. Fragments shorter
# than SENTENCE_MIN_CHARS ("Ji.") are merged into the next sentence, so no clip
# is a bare syllable. Decimals ("1.5 kg") never match: no whitespace follows
# the dot. Found by reading the voice-agent tutorial (arXiv 2603.05413), which
# uses the same two rules; see MD/research_papers.md, method M1.
_BOUNDARY = re.compile(r'[.!?।]+(?=\s)')
_NO_SPLIT_AFTER = frozenset({
    "rs", "inr", "mr", "mrs", "ms", "dr", "sri", "smt", "no", "nos", "st", "vs", "approx",
})
SENTENCE_MIN_CHARS = int(os.getenv("SENTENCE_MIN_CHARS", "8"))


def next_sentence(buffer: str, min_chars: int | None = None):
    """
    The first complete sentence in `buffer`, as (sentence, rest), or None when
    the buffer holds no finished sentence yet. A sentence ends at . ! ? or the
    Hindi danda followed by whitespace, except after an abbreviation or when it
    would be shorter than min_chars.
    """
    min_chars = SENTENCE_MIN_CHARS if min_chars is None else min_chars
    for m in _BOUNDARY.finditer(buffer):
        before = buffer[:m.start()].split()
        last_word = before[-1].lower().strip("(\"'") if before else ""
        if m.group(0) == "." and last_word in _NO_SPLIT_AFTER:
            continue
        sentence = buffer[:m.end()].strip()
        if len(sentence) < min_chars:
            continue
        return sentence, buffer[m.end():].lstrip()
    return None

# 2026-08-17: an earlier version of this function split the first
# sentence early at its first comma to start TTS sooner (measured
# real gain — see [SPAN] llm_ttfs_ms in dukaan_dost/app.py). Reverted
# same day: the "rest of sentence" clip needed a fresh TTS call that
# routinely took longer than playback_thread's TTS_CONTINUATION_WAIT_
# SEC (150ms, tuned for a different, faster case — Google TTS's own
# internal prefix/rest audio-chunk split, where the "rest" is already
# mid-flight). When it missed that window, playback_thread treated it
# as a new, unrelated reply instead of a continuation — full echo-tail
# mute + checkpoint gap landing MID-SENTENCE, heard on a real call as
# the bot's voice cutting out/lagging. Simple full-sentence chunking
# doesn't have this failure mode, at the cost of the latency win.

_LANGUAGE_DISPLAY_NAMES = {
    "en-in": "English",
    "hi-in": "Hindi",
    "te-in": "Telugu",
}


def _language_display_name(language_code: str) -> str:
    return _LANGUAGE_DISPLAY_NAMES.get((language_code or "").lower(), language_code or "English")


class ConversationManager:
    def __init__(self, shop_dir, llm_model: str, max_tokens: int, temperature: float):
        self.shop_dir = shop_dir
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.temperature = temperature

        config_path = shop_dir / "config.yaml"
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.base_prompt = self.config["system_prompt"]
        self.fallback_messages = {
            lang.lower(): msg for lang, msg in self.config["fallback_messages"].items()
        }

        self.core_context = get_core_context(shop_dir)

    def _fallback_for(self, detected_language: str) -> str:
        key = (detected_language or "en-in").lower()
        return self.fallback_messages.get(key, self.fallback_messages["en-in"])

    def _build_system_prompt(self, context: str, knowledge: str, detected_language: str, is_first_turn: bool) -> str:
        parts = [self.base_prompt]

        if is_first_turn:
            parts.append("This is the first message of the call — the automatic greeting has already been spoken.")
        else:
            parts.append("This is a continuing conversation, not the start of the call — do not greet again.")

        if detected_language:
            lang_name = _language_display_name(detected_language)
            parts.append(
                f"The caller's detected language for this turn is: {lang_name}. "
                f"The most recent user message below will also start with a short "
                f"parenthetical reminder of this, e.g. \"(Reply in {lang_name}.)\" — "
                f"that reminder is guidance for you only, never part of what the "
                f"caller actually said, and must never be echoed, translated, or "
                f"referenced in your reply."
            )

        if context:
            parts.append(context)

        if self.core_context:
            parts.append(self.core_context)

        if knowledge:
            parts.append("Relevant knowledge for this query:\n" + knowledge)
        else:
            log.debug("[KNOWLEDGE] no relevant sections retrieved for this turn")

        return "\n\n".join(parts)

    def _build_messages(self, transcript: str, recent_history: list[dict], context: str, detected_language: str):
        is_first_turn = not recent_history
        # get_relevant_context_maybe_cached() must see the caller's
        # actual words, not the language-reminder wrapper added below,
        # so this uses the raw transcript, before any modification.
        # Reuses a speculative retrieval kicked off in recorder_thread
        # on an earlier interim STT transcript (while the caller was
        # still talking) if the final transcript is consistent with
        # it, falling back to a normal (still fast, local) lookup
        # otherwise — see knowledge_retriever.py for why this is a
        # modest, not dramatic, win.
        knowledge = get_relevant_context_maybe_cached(self.shop_dir, transcript)
        system_prompt = self._build_system_prompt(context, knowledge, detected_language, is_first_turn)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(recent_history)

        # The system prompt's language-detected line sits far from the
        # actual generation point once a few prior turns exist — Vertex
        # AI's system_instruction is structurally separate from the
        # conversation turns, and a several-turns-old Hindi conversation
        # pattern in recent_history was observed outweighing that single
        # upfront line, producing Hindi text even when this turn was
        # correctly tagged Telugu. Repeating the reminder here, inline
        # with the newest turn, puts it at the position closest to where
        # Gemini actually generates, which carries far more weight.
        user_content = transcript
        if detected_language:
            lang_name = _language_display_name(detected_language)
            user_content = f"(Reply in {lang_name}.) {transcript}"

        messages.append({"role": "user", "content": user_content})
        return messages, is_first_turn

    def handle_turn(self, transcript: str, recent_history: list[dict], context: str, detected_language: str):
        """Blocking — returns (reply_text, reply_language)."""
        messages, is_first_turn = self._build_messages(transcript, recent_history, context, detected_language)

        reply = gemini_ask(
            model=self.llm_model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        reply = validate_reply(
            reply,
            self._fallback_for(detected_language),
            is_first_turn,
            language_code=detected_language or "",
        )

        return reply, detected_language or "en-IN"

    def handle_turn_streaming(self, transcript: str, recent_history: list[dict], context: str, detected_language: str):
        """
        Yields (sentence_chunk, reply_language) tuples as Gemini streams.

        Buffers incoming text and flushes at sentence boundaries (. ! ? ।)
        so each yielded chunk is a speakable sentence. A final flush at
        the end emits whatever remains in the buffer.

        The caller is responsible for validation and history — the full
        reply text must be assembled from the yielded chunks.
        """
        messages, _ = self._build_messages(transcript, recent_history, context, detected_language)
        reply_language = detected_language or "en-IN"

        buffer = ""
        for chunk in gemini_stream(
            model=self.llm_model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        ):
            buffer += chunk

            while True:
                found = next_sentence(buffer)
                if found is None:
                    break
                sentence, buffer = found
                yield sentence, reply_language

        remainder = buffer.strip()
        if remainder:
            yield remainder, reply_language
