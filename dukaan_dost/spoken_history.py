"""
spoken_history.py

Keeps the conversation history honest when a caller interrupts.

The reply is generated and queued for speech long before it finishes playing. If
the caller cuts in after the first sentence, the history would still say the agent
announced all of it ("Added atta. Added sugar. Anything else?"), and the model
would carry on as if the caller had heard that sugar was added. For an order that
is a wrong cart waiting to happen.

This records, per reply, which sentences were queued and how many audio clips each
needed, and counts the clips that played to the end. After an interruption the
history keeps only the sentences whose clips ALL finished. A sentence that was cut
off part-way counts as not heard, so the model re-confirms it instead of assuming.
(Method M2 in MD/research_papers.md, from ChipChat, arXiv 2509.00078.)

Threading: planned() is called by the processor thread, clip_finished() by the
playback thread, trim_after_interrupt() by either. Each takes this object's own
lock. trim_after_interrupt() edits the history list it is given, so the caller must
hold whatever lock guards that list; this object's lock is never held while the
caller's is requested, so the two cannot deadlock.
"""

import threading

_KEEP_REPLIES = 64          # replies remembered; older ones are forgotten


class SpokenTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._plan = {}         # reply_id -> [(sentence, n_clips)]
        self._played = {}       # reply_id -> clips that played to the end
        self._entries = {}      # reply_id -> (user_entry, assistant_entry), the dicts in the history list

    def forget(self) -> None:
        with self._lock:
            self._plan.clear()
            self._played.clear()
            self._entries.clear()

    def planned(self, reply_id, sentence: str, n_clips: int) -> None:
        """A sentence was synthesised and queued as n_clips audio clips."""
        if n_clips <= 0:
            return
        with self._lock:
            self._plan.setdefault(reply_id, []).append((sentence, n_clips))
            while len(self._plan) > _KEEP_REPLIES:
                oldest = next(iter(self._plan))
                self._plan.pop(oldest, None)
                self._played.pop(oldest, None)
                self._entries.pop(oldest, None)

    def clip_finished(self, reply_id) -> None:
        """One clip of this reply played to the end (it was not cut off)."""
        with self._lock:
            self._played[reply_id] = self._played.get(reply_id, 0) + 1

    def register_entry(self, reply_id, user_entry: dict, assistant_entry: dict) -> None:
        with self._lock:
            self._entries[reply_id] = (user_entry, assistant_entry)

    def heard_text(self, reply_id) -> str:
        """The sentences of this reply whose clips all played to the end."""
        with self._lock:
            plan = list(self._plan.get(reply_id, []))
            played = self._played.get(reply_id, 0)
        heard, used = [], 0
        for sentence, n_clips in plan:
            if used + n_clips > played:
                break
            used += n_clips
            heard.append(sentence)
        return " ".join(heard).strip()

    def trim_after_interrupt(self, reply_id, history: list):
        """
        Make `history` say only what the caller heard of this reply. Returns the heard text
        ("" if nothing was heard), or None if the reply has no entry in the history (yet).
        If nothing was heard the caller's turn and the unheard reply are both removed, so the
        history still alternates user / assistant.
        """
        with self._lock:
            entries = self._entries.get(reply_id)
        if entries is None:
            return None
        user_entry, assistant_entry = entries
        if not any(e is assistant_entry for e in history):
            return None
        heard = self.heard_text(reply_id)
        if heard:
            assistant_entry["content"] = heard
        else:
            history[:] = [e for e in history if e is not assistant_entry and e is not user_entry]
        return heard
