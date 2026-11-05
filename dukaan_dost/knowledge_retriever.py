
"""
knowledge_retriever.py

Two layers of knowledge:

1. ALWAYS-ON CORE (knowledge/core/always_on.md) — identity, language
   switching rules, general bot behavior rules, escalation triggers.
   This is small enough and universally relevant enough that it gets
   loaded into EVERY reply, regardless of topic.

2. CROSS-FILE RETRIEVAL — every ## section across every topic file in
   knowledge/ is scored against the transcript by keyword overlap; the
   top-scoring sections (up to MAX_CONTEXT_CHARS) are returned. This
   replaces the old per-intent single-file lookup: instead of trusting
   an upstream classifier to pick the one right file, every topic is
   searched directly, so a query that touches two topics (e.g.
   "product price and delivery time") can still pull sections from
   both products_pricing.md and delivery_shipping.md.

No vector DB here on purpose: on a small machine, spinning up a
sentence-transformer model just to search a handful of small markdown
files is unnecessary weight. Section-level keyword matching is fast
and good enough for structured docs (pricing tables, FAQ entries). If
you later have dozens of long documents per topic, that's the point
where real embeddings would start to pay for themselves.
"""

import logging
import re
import threading
from pathlib import Path

log = logging.getLogger("knowledge_retriever")

# Topic files searched on every turn (all of them — no upstream
# classifier picks a subset anymore).
KNOWLEDGE_FILES = [
    "products_pricing.md",
    "ordering_payment.md",
    "delivery_shipping.md",
    "packaging.md",
    "refund_policy.md",
    "payment_issues.md",
    "faq.md",
    "recommendations.md",
]

MAX_CONTEXT_CHARS = 1200  # keep the LLM prompt small and fast

# What counts as a letter of a word. Python's \w does not include the vowel signs
# and other combining marks of Indian scripts (the "ा" of "आटा", the "ి" of
# "పిండి"), so a plain \w+ cut every Hindi and Telugu word into fragments
# ("आटा" became "आट") and keyword retrieval was mostly noise for them. The block
# U+0900-U+0DFF covers Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil,
# Telugu, Kannada and Malayalam, complete with their marks.
_WORD_CHARS = r"\w\u0900-\u0DFF"
_TOKEN = re.compile(rf"[{_WORD_CHARS}]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


# Words that say nothing about WHICH product or topic the caller means. Left in, "what is the price of
# ghee" scored a long generic FAQ section (the, is, price, of) above the one-line ghee section (ghee), and
# the model was then told, with confidence, that the shop had no ghee. "do" is the Hindi for two.
_STOPWORDS = frozenset("""
a an the i me my we you your is are am was were be been of to in on at for from and or it its this that these those
what which who when where how much many some any please want need can could would will shall do does did
hai hain ho tha thi ka ki ke ko se me mein main mai aur ya kya kitna kitne kitni chahiye chahie dena dedo de
bhi to yeh ye woh wo is us isko usko mujhe mera meri mere aap aapka
""".split())


CORE_FILENAME = "core/always_on.md"

# path -> (mtime, [sections]). Avoids re-reading and re-splitting every
# knowledge file on every single turn when nothing has changed, while
# still picking up edits (e.g. the owner updating a price) without
# needing to restart the process — checked via mtime, not a one-time
# load.
_sections_cache: dict[Path, tuple[float, list[str]]] = {}
# 2026-07-31: read/written from both prefetch_relevant_context() (a
# background/recorder-thread caller) and get_relevant_context_maybe_
# cached() (the main turn-processing thread) — unlike _speculative_lock
# below, which protects a similarly-shared cache in this same module,
# this one had no lock. Not a corruption risk (dict ops are atomic
# under the GIL), but two threads racing a cache miss for the same file
# both re-read and re-split it before either writes back — wasted I/O,
# and an inconsistency in this module's own locking discipline that
# could confuse a future reader into thinking only half needs it.
_sections_cache_lock = threading.Lock()


def _split_sections(text: str) -> list[str]:
    """Split a markdown doc into sections on ## headers (falls back to whole doc)."""
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    return [s.strip() for s in sections if s.strip()]


def _get_sections(file_path: Path) -> list[str]:
    with _sections_cache_lock:
        mtime = file_path.stat().st_mtime
        cached = _sections_cache.get(file_path)
        if cached and cached[0] == mtime:
            return cached[1]

        sections = _split_sections(file_path.read_text(encoding="utf-8"))
        _sections_cache[file_path] = (mtime, sections)
        return sections


def _score_section(section: str, query_words: set[str]) -> int:
    """
    Word-boundary matching, not plain substring — otherwise a query
    word like "confirm" also matches unrelated occurrences of
    "confirmation" (boilerplate like "prepared after order
    confirmation" in product tables), diluting the score of the
    section the query is actually about.
    """
    # A word counts 3 when it is in the section's heading (the item's name in three languages), 2 when it is
    # in the "Also called" line (spellings callers use), 1 anywhere else.
    lines = section.lower().splitlines()
    heading = lines[0] if lines else ""
    also = next((ln for ln in lines if ln.startswith("also called")), "")
    rest = "\n".join(lines[1:])

    def has(word, text):
        return re.search(rf"(?<![{_WORD_CHARS}]){re.escape(word)}(?![{_WORD_CHARS}])", text) is not None

    score = 0
    for word in query_words:
        if has(word, heading):
            score += 3
        elif has(word, also):
            score += 2
        elif has(word, rest):
            score += 1
    return score


def get_core_context(shop_dir: Path) -> str:
    """Always-on core knowledge — loaded in full on every turn."""
    core_path = shop_dir / "knowledge" / CORE_FILENAME
    if not core_path.exists():
        log.warning(f"[KNOWLEDGE] missing always-on core file: {core_path}")
        return ""
    return core_path.read_text(encoding="utf-8")


def get_relevant_context(shop_dir: Path, transcript: str, skip: tuple = ()) -> str:
    """
    Scores every section of every topic file in knowledge/ against the
    transcript and returns the top-matching sections, up to
    MAX_CONTEXT_CHARS. Returns "" if no file has any keyword overlap.
    """
    query_words = _tokens(transcript)
    informative = query_words - _STOPWORDS
    if informative:
        query_words = informative
    if not query_words:
        return ""

    scored_sections = []  # list of (score, section_text)
    knowledge_dir = shop_dir / "knowledge"

    for filename in KNOWLEDGE_FILES:
        if filename in skip:
            continue
        file_path = knowledge_dir / filename
        if not file_path.exists():
            continue

        for section in _get_sections(file_path):
            score = _score_section(section, query_words)
            if score > 0:
                scored_sections.append((score, section))

    if not scored_sections:
        log.debug(f"[KNOWLEDGE] no matching sections for: '{transcript}'")
        return ""

    scored_sections.sort(key=lambda item: item[0], reverse=True)

    context = ""
    for _, section in scored_sections:
        if len(context) + len(section) > MAX_CONTEXT_CHARS:
            break
        context += section + "\n\n"

    return context.strip() or scored_sections[0][1][:MAX_CONTEXT_CHARS]


# ─────────────────────────────────────────────────────
# SPECULATIVE RETRIEVAL — retrieval here is already fast (local
# keyword scoring, no network, cached file reads), so the win from
# running it "speculatively" is genuinely modest — a few milliseconds,
# not the seconds-level wins elsewhere in this pipeline. What it does
# buy: that small cost now overlaps the time the caller is STILL
# TALKING (via streaming STT's interim/partial transcripts) instead of
# happening only after they've finished, which was previously dead
# time downstream (Gemini/TTS can't start until retrieval is done
# anyway). Kept intentionally simple given the small expected payoff —
# a single-slot cache, not a full per-turn keyed store, on the
# reasoning that only one utterance is ever actually in flight at a
# time in this pipeline's threading model.
# ─────────────────────────────────────────────────────

_speculative_lock = threading.Lock()
_speculative_partial = ""
_speculative_context: str | None = None
_speculative_source = None       # (shop folder, signature of its knowledge files) the cached context was built from


def _source_key(shop_dir: Path):
    """Which shop and which version of its files a context came from. A cached context is reused only for the same
    shop and unchanged files: otherwise the last call of one shop (or a price just edited in the admin page) could
    answer the next caller of another shop (or the same shop) with the wrong prices."""
    folder = Path(shop_dir) / "knowledge"
    sig = []
    try:
        for f in sorted(folder.rglob("*.md")):
            sig.append((str(f.relative_to(folder)), f.stat().st_mtime_ns))
    except OSError:
        pass
    return (str(Path(shop_dir).resolve()), tuple(sig))


def prefetch_relevant_context(shop_dir: Path, partial_transcript: str) -> None:
    """
    Speculatively computes and caches the RAG context for a still-in-
    progress utterance's latest interim transcript. Call this from a
    background thread — it does the same work get_relevant_context()
    does, just earlier, on a partial rather than the final transcript.
    """
    global _speculative_partial, _speculative_context, _speculative_source
    source = _source_key(shop_dir)
    context = get_relevant_context(shop_dir, partial_transcript)
    with _speculative_lock:
        _speculative_partial = partial_transcript
        _speculative_context = context
        _speculative_source = source


def get_relevant_context_maybe_cached(shop_dir: Path, final_transcript: str) -> str:
    """
    Reuses a speculative result from prefetch_relevant_context() if the
    final transcript's words are a superset of what the speculative
    call was based on — retrieval is coarse topic-matching, so a final
    transcript that just continues past its own earlier partial almost
    always still matches the same sections. Falls back to a normal
    (still fast, local) call otherwise, so this is never worse than
    the non-speculative path, only sometimes faster.
    """
    with _speculative_lock:
        cached_partial = _speculative_partial
        cached_context = _speculative_context
        cached_source = _speculative_source

    if cached_partial and cached_context is not None and cached_source == _source_key(shop_dir):
        partial_words = _tokens(cached_partial)
        final_words = _tokens(final_transcript)
        if partial_words and partial_words.issubset(final_words):
            log.debug(f"[KNOWLEDGE] Reusing speculative context (partial: '{cached_partial}')")
            return cached_context

    return get_relevant_context(shop_dir, final_transcript)
