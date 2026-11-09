"""
live_feed.py

What the shopkeeper's dashboard shows while a call is happening: the conversation so far, the order being built and
the loan quote. It lives in MEMORY ONLY, for the length of the call:
  - nothing here is written to disk, logged or put in a record (the saved call record still keeps counts only, call_stats.py);
  - when a call ends, or another call begins, the previous one is gone;
  - it reaches only the signed-in dashboard (dashboard.py), never the public call page.

The agent already describes each call to the caller's page as small events (transport.send_event): what the caller
said ("user"), what the agent said ("agent", in pieces that share a reply id), the order so far ("order") and the
quote ("loan"). The browser transport sends those to the page; this keeps a copy of them for the dashboard, which also
makes a phone call visible, because a phone provider's socket gets none of those events (transport_telephony.send_event).
Several threads call add() and view(), so every method takes a lock.
"""

import threading

MAX_LINES = 60                # the last 60 lines of the conversation
MAX_TEXT = 600                # characters kept of one line; a longer one is cut
_PRIMITIVES = (str, int, float, bool, type(None))


def _text(value) -> str:
    return str(value or "").strip()[:MAX_TEXT]


def _plain(d: dict) -> dict:
    """A shallow copy of d with only plain JSON values, so nothing odd is ever sent to a page."""
    return {str(k): v for k, v in d.items() if isinstance(v, _PRIMITIVES)}


class LiveFeed:
    def __init__(self):
        self._lock = threading.Lock()
        self._reset(None)

    def _reset(self, call_id) -> None:
        self._call = call_id
        self._lines = []
        self._reply = None
        self._order = None
        self._loan = None
        self._language = None

    def add(self, call_id, event: dict) -> None:
        """Take one event of the call `call_id`. A different call id starts a fresh feed. Never raises."""
        try:
            kind = event.get("type") if isinstance(event, dict) else None
            with self._lock:
                if call_id != self._call:
                    self._reset(call_id)
                if kind == "user":
                    text = _text(event.get("text"))
                    if text:
                        self._lines.append({"who": "caller", "text": text})
                        self._reply = None
                    if event.get("lang"):
                        self._language = str(event.get("lang"))[:16]
                elif kind == "agent":
                    text, reply = _text(event.get("text")), event.get("reply")
                    if not text:
                        return
                    last = self._lines[-1] if self._lines else None
                    if last is not None and last["who"] == "agent" and reply is not None and reply == self._reply:
                        last["text"] = (last["text"] + " " + text)[:MAX_TEXT]       # one reply arrives in pieces
                    else:
                        self._lines.append({"who": "agent", "text": text})
                        self._reply = reply
                elif kind == "order":
                    items = [_plain(i) for i in (event.get("items") or []) if isinstance(i, dict)]
                    total = event.get("total")
                    self._order = {"total": total if isinstance(total, (int, float)) else 0, "items": items}
                elif kind == "loan":
                    self._loan = _plain(event)
                    self._loan.pop("type", None)
                if len(self._lines) > MAX_LINES:
                    del self._lines[:len(self._lines) - MAX_LINES]
        except Exception:
            pass                                 # a note for the dashboard must never affect the call

    def view(self, call_id) -> dict:
        """The feed of call `call_id` as the dashboard reads it; empty if that is not the call being kept."""
        with self._lock:
            if call_id != self._call:
                return {"language": None, "lines": [], "order": None, "loan": None}
            return {"language": self._language, "lines": [dict(x) for x in self._lines],
                    "order": None if self._order is None else {"total": self._order["total"], "items": [dict(i) for i in self._order["items"]]},
                    "loan": None if self._loan is None else dict(self._loan)}

    def clear(self) -> None:
        with self._lock:
            self._reset(None)
