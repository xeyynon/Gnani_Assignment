"""
call_stats.py

A tally of one call, so the dashboard can show that a call happened even when nothing was ordered, and why
(a rate limit, a noisy line, the caller talking over the agent). It keeps COUNTS ONLY: no words, no audio, and
never the caller's phone number. Call recording stays off (rule: synthetic data only, no recorded calls).

The agent calls begin() when a call starts, turn() for every thing the caller says that is understood,
barge_in() when the caller cuts a reply short, no_speech() when speech was detected but nothing was
recognised, and finish() when the call ends; finish() returns the record that store.write_call() saves.
Several threads call these, so every method takes a lock.
"""

import threading
import time
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


class CallStats:
    def __init__(self):
        self._lock = threading.Lock()
        self._clear()

    def _clear(self):
        self._started_mono = None
        self._started_wall = None
        self._shop = ""
        self._channel = "browser"
        self._language = None
        self._turns = 0
        self._barge_ins = 0
        self._no_speech = 0
        self._model_failures = 0

    def begin(self, shop: str = "") -> None:
        """A call has started. A call still open (its end was missed) is dropped, not mixed into the new one."""
        with self._lock:
            self._clear()
            self._started_mono = time.monotonic()
            self._started_wall = datetime.now(IST)
            self._shop = shop or ""

    def active(self) -> bool:
        with self._lock:
            return self._started_mono is not None

    def set_channel(self, node: str) -> None:
        """The transport names its node after the way the call came in: "phone-<id>" for a phone provider."""
        with self._lock:
            if self._started_mono is not None:
                self._channel = "phone" if str(node or "").startswith("phone") else "browser"

    def turn(self, language: str | None = None) -> None:
        with self._lock:
            if self._started_mono is not None:
                self._turns += 1
                if language:
                    self._language = language

    def barge_in(self) -> None:
        with self._lock:
            if self._started_mono is not None:
                self._barge_ins += 1

    def no_speech(self) -> None:
        with self._lock:
            if self._started_mono is not None:
                self._no_speech += 1

    def model_failure(self) -> None:
        """A turn where the language model gave no usable answer (a rate limit, a timeout)."""
        with self._lock:
            if self._started_mono is not None:
                self._model_failures += 1

    def finish(self, outcome: str, order_id: str | None = None, total: int | None = None,
               status: str | None = None) -> dict | None:
        """The record for this call, and the tally is cleared. None if no call was open (so a call whose end is
        reported twice is saved once)."""
        with self._lock:
            if self._started_mono is None:
                return None
            wall = self._started_wall
            record = {
                "call_id": wall.strftime("%Y%m%d-%H%M%S") + f"-{wall.microsecond // 1000:03d}",
                "time": wall.isoformat(),
                "shop": self._shop,
                "channel": self._channel,
                "seconds": max(0, int(round(time.monotonic() - self._started_mono))),
                "language": self._language,
                "turns": self._turns,
                "barge_ins": self._barge_ins,
                "no_speech": self._no_speech,
                "model_failures": self._model_failures,
                "outcome": outcome,
            }
            if order_id:
                record["order_id"] = order_id
            if total is not None:
                record["total"] = total
            if status:
                record["status"] = status
            self._clear()
            return record


CURRENT = CallStats()          # the one call at a time that the agent is serving
