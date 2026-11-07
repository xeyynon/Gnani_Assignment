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

from .knowledge_retriever import get_core_context, get_relevant_context, get_relevant_context_maybe_cached
from . import loan_turn, order_turn
from .call_stats import CURRENT as _call_stats
from .product_search import ProductSearch, normalise
from . import stock as _stock
from .llm_provider import ask as gemini_ask, ask_json as gemini_ask_json, stream as gemini_stream     # Gemini or Groq, by LLM_PROVIDER
from .validator import validate_reply

log = logging.getLogger("conversation_manager")

# Where a streamed reply is cut into speakable sentences. A full stop is NOT a
# sentence end after an abbreviation: "Rs. 260 hai" must stay one clip, because
# each clip is spoken separately with a listening pause between them, and a
# price split from its currency word is heard as a stumble. Fragments shorter
# than SENTENCE_MIN_CHARS ("Ji.") are merged into the next sentence, so no clip
# is a bare syllable. Decimals ("1.5 kg") never match: no whitespace follows
# the dot. Found by reading the voice-agent tutorial (arXiv 2603.05413), which
# uses the same two rules.
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
        # Order turns use a shorter persona (the order instructions carry the order rules): about 2,000
        # fewer characters a turn, which matters for the model's daily token limit and for latency.
        self.order_base_prompt = self.config.get("order_system_prompt") or self.base_prompt
        self.fallback_messages = {
            lang.lower(): msg for lang, msg in self.config["fallback_messages"].items()
        }

        self.core_context = get_core_context(shop_dir)

        # A shop with a stock.json takes orders through the order flow (order_turn.py): the model
        # says which items and how many, the code checks the stock and does all the sums.
        try:
            self.stock_items = _stock.load(shop_dir)
        except FileNotFoundError:
            self.stock_items = []
        except Exception as e:      # a malformed stock.json (any shape of it) must not stop the shop's calls (B-67)
            log.warning(f"[ORDER] {shop_dir.name}: the stock list is unusable, order taking is off: {e}")
            self.stock_items = []
        # the JSON note needs more room than plain speech; gpt-oss models spend part of the budget reasoning first
        # How the order prompt shows the products: "full" sends every item on every turn;
        # "search" sends only the best matches of the caller's sentence (product_search.py) plus the ones already
        # in the order; "auto" (default) sends everything while the catalogue is small and searches when it grows.
        self.catalogue_mode = os.getenv("ORDER_CATALOGUE", "auto").strip().lower()
        self.catalogue_auto_max_chars = int(os.getenv("ORDER_CATALOGUE_AUTO_MAX_CHARS", "6000"))
        self.catalogue_candidates = int(os.getenv("ORDER_CATALOGUE_CANDIDATES", "12"))
        try:
            self.product_search = ProductSearch(self.stock_items) if self.stock_items else None
        except Exception as e:
            log.warning(f"[ORDER] {shop_dir.name}: product search could not be built: {e}")
            self.product_search = None
        self._product_names = None          # every spelling of every product, built the first time names_product() needs it
        self.order_tokens = int(os.getenv("ORDER_LLM_TOKENS") or (700 if llm_model.startswith("openai/gpt-oss") else 260))
        self.order_temperature = float(os.getenv("ORDER_LLM_TEMP", "0.2"))   # reading an order is extraction, not chat

    def named_skus(self, text: str) -> set:
        """
        The SKUs whose name or alias, in any language, the caller's words contain, or match almost exactly. Used to
        tell an order turn from a plain repeat request (B-69), and to tell which ops of the model's note the caller
        actually asked for (OrderSession.drop_replayed_ops).
        """
        if not self.stock_items:
            return set()
        if self._product_names is None:
            by_sku = {}
            for it in self.stock_items:
                try:
                    n = it["name"]
                    spellings = set()
                    for raw in (n["en"], re.sub(r"\s*\(.*?\)", "", n["en"]), n["hi"], n["te"], *it.get("aliases", [])):
                        v = normalise(str(raw))
                        if len(v) >= 3 or (v and not v.isascii()):
                            spellings.add(v)
                    by_sku[it["sku"]] = spellings
                except Exception:
                    continue
            self._product_names = by_sku
        padded = f" {normalise(text)} "
        found = {sku for sku, spellings in self._product_names.items() if any(f" {v} " in padded for v in spellings)}
        try:
            if self.product_search:
                found |= {sku for sku, score in self.product_search.search(text, 3) if score >= 0.9}
        except Exception:
            pass
        return found

    def names_product(self, text: str) -> bool:
        """True if the caller's words name one of the shop's products (see named_skus)."""
        return bool(self.named_skus(text))

    def _fallback_for(self, detected_language: str) -> str:
        key = (detected_language or "en-in").lower()
        return self.fallback_messages.get(key, self.fallback_messages["en-in"])

    def _build_system_prompt(self, context: str, knowledge: str, detected_language: str, is_first_turn: bool,
                             base: str | None = None) -> str:
        parts = [base or self.base_prompt]

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

    def _build_messages(self, transcript: str, recent_history: list[dict], context: str, detected_language: str,
                        base: str | None = None, knowledge: str | None = None):
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
        if knowledge is None:
            knowledge = get_relevant_context_maybe_cached(self.shop_dir, transcript)
        system_prompt = self._build_system_prompt(context, knowledge, detected_language, is_first_turn, base)

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

    def _closing_for(self, payment, language):
        """The shop's fixed sentence for when payment has been chosen (config: order_closing, order_closing_credit)."""
        table = self.config.get("order_closing_credit" if payment == "udhaar" else "order_closing") or {}
        table = {str(k).lower(): v for k, v in table.items()}
        return table.get((language or "en-in").lower()) or table.get("en-in")

    def catalogue_for(self, transcript: str, order) -> str:
        """The product list for one order turn: all items, or the best matches plus what is already ordered."""
        full = _stock.catalogue_text(self.stock_items)
        mode = self.catalogue_mode
        if mode == "auto":
            mode = "full" if len(full) <= self.catalogue_auto_max_chars else "search"
        if mode != "search" or self.product_search is None:
            return full
        wanted = {sku for sku, _ in self.product_search.search(transcript, self.catalogue_candidates)}
        wanted |= set(order.lines)                       # a correction names an item already in the order
        return _stock.catalogue_text(self.stock_items, only=wanted)

    def _order_turn(self, transcript: str, recent_history: list[dict], context: str, detected_language: str, order):
        """
        One turn of order taking: ask the model for a JSON note (items, quantities, payment, finish, a
        short reply), apply it to `order` (which checks the stock list and does the sums), and yield
        the reply as sentences, with the amounts written by the code.
        """
        examples = [(it["sku"], it["name"]["en"], it["unit"]) for it in self.stock_items[:2]]
        full_context = "\n\n".join(part for part in (
            context, order_turn.prompt_section(examples), self.catalogue_for(transcript, order),
            order.state_for_model()) if part)
        # The catalogue replaces the product sections of the knowledge search; the search still supplies shop
        # facts (delivery, payment, opening hours).
        facts = get_relevant_context(self.shop_dir, transcript, skip=("products_pricing.md",))
        messages, _ = self._build_messages(transcript, recent_history, full_context, detected_language,
                                           base=self.order_base_prompt, knowledge=facts)
        reply_language = detected_language or "en-IN"

        raw = gemini_ask_json(model=self.llm_model, messages=messages, max_tokens=self.order_tokens,
                              temperature=self.order_temperature, schema=order_turn.SCHEMA)
        plan = order_turn.parse_plan(raw)
        if plan is None and raw.strip():
            # The model answered in plain words (it tends to when asked for something out of stock). Plain
            # words cannot be trusted to match the order, so ask once more for the JSON note.
            log.warning(f"[ORDER] plain text instead of the JSON note, asking again: {raw[:160]!r}")
            retry = messages + [{"role": "assistant", "content": raw},
                                {"role": "user", "content": "That was not the JSON object. Answer again with only "
                                 "the JSON object described above, for the caller's last message."}]
            raw = gemini_ask_json(model=self.llm_model, messages=retry, max_tokens=self.order_tokens,
                                  temperature=self.order_temperature, schema=order_turn.SCHEMA)
            plan = order_turn.parse_plan(raw)
        if plan is None:
            log.warning(f"[ORDER] the model's answer was not usable JSON: {raw[:200]!r}")
            _call_stats.model_failure()
            yield self._fallback_for(detected_language), reply_language
            return

        plan.say = validate_reply(plan.say, self._fallback_for(detected_language), not recent_history,
                                  language_code=detected_language or "") if plan.say else ""
        plan.ops, replayed = order.drop_replayed_ops(plan.ops, self.named_skus(transcript), order_turn.has_quantity(transcript))
        if replayed:
            log.warning(f"[ORDER] the model repeated changes the caller did not just ask for, ignored: {replayed}")
        result = order.apply(plan.ops, plan.payment, plan.customer_name, plan.delivery, plan.finish,
                             language=reply_language, balance_query=plan.balance_query)
        text = order_turn.compose(plan, result, order, detected_language,
                                  closing=self._closing_for("cash" if order.credit_state == "approved" else order.payment,
                                                            detected_language))
        if not text:
            yield self._fallback_for(detected_language), reply_language
            return

        buffer = text
        while True:
            found = next_sentence(buffer)
            if found is None:
                break
            sentence, buffer = found
            yield sentence, reply_language
        if buffer.strip():
            yield buffer.strip(), reply_language

    def _loan_turn(self, transcript: str, recent_history: list[dict], context: str, detected_language: str, loan):
        """
        One turn of loan guidance: the model reads the amount out of the caller's words (JSON), loan_session.py
        checks it and does the arithmetic, and the reply is the code's sentences (see loan_turn.compose).
        """
        loan.active = True
        reply_language = detected_language or "en-IN"
        full_context = "\n\n".join(part for part in (context, loan_turn.prompt_section()) if part)
        messages, _ = self._build_messages(transcript, recent_history, full_context, detected_language,
                                           base=self.order_base_prompt, knowledge="")
        raw = gemini_ask_json(model=self.llm_model, messages=messages, max_tokens=self.order_tokens,
                              temperature=self.order_temperature, schema=loan_turn.SCHEMA)
        plan = loan_turn.parse_plan(raw)
        if plan is None and raw.strip():
            log.warning(f"[LOAN] plain text instead of the JSON note, asking again: {raw[:160]!r}")
            retry = messages + [{"role": "assistant", "content": raw},
                                {"role": "user", "content": "That was not the JSON object. Answer again with only "
                                 "the JSON object described above, for the caller's last message."}]
            raw = gemini_ask_json(model=self.llm_model, messages=retry, max_tokens=self.order_tokens,
                                  temperature=self.order_temperature, schema=loan_turn.SCHEMA)
            plan = loan_turn.parse_plan(raw)
        if plan is None:
            log.warning(f"[LOAN] the model's answer was not usable JSON: {raw[:200]!r}")
            _call_stats.model_failure()
            yield self._fallback_for(detected_language), reply_language
            return
        result = loan.apply(plan.amount, plan.kind, plan.business, plan.place, language=reply_language)
        text = loan_turn.compose(plan, result, loan, detected_language)
        buffer = text
        while True:
            found = next_sentence(buffer)
            if found is None:
                break
            sentence, buffer = found
            yield sentence, reply_language
        if buffer.strip():
            yield buffer.strip(), reply_language

    def handle_turn_streaming(self, transcript: str, recent_history: list[dict], context: str, detected_language: str,
                              order=None, loan=None):
        """
        Yields (sentence_chunk, reply_language) tuples as Gemini streams.

        Buffers incoming text and flushes at sentence boundaries (. ! ? ।)
        so each yielded chunk is a speakable sentence. A final flush at
        the end emits whatever remains in the buffer.

        The caller is responsible for validation and history — the full
        reply text must be assembled from the yielded chunks.
        """
        if loan is not None and (loan.active or loan_turn.detect(transcript)):
            yield from self._loan_turn(transcript, recent_history, context, detected_language, loan)
            return
        if order is not None and self.stock_items:
            yield from self._order_turn(transcript, recent_history, context, detected_language, order)
            return

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
