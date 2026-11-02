"""
transport_websocket.py

The call transport: a web page in a browser is the "phone". The page captures
the microphone, resamples it to 16 kHz and streams it over a WebSocket; the
agent's replies come back the same way and the page plays them. Nothing but
Python and a browser is needed (DEC-032).

One small server (the `websockets` package) does both jobs on one port. Several
shops share it (DEC-034): the call link picks the shop.
    GET /s/<shop>/      the call page for that shop (dukaan_dost/web/index.html)
    WS  /s/<shop>/ws    a call for that shop
    GET /, WS /ws       the same for the default shop
Other HTTP routes (the dashboards) are added with add_http_handler().

Protocol (one call at a time; a second visitor is told "busy"):
    page -> server   binary: 16 kHz mono s16le PCM, any chunk size
                     text:   {"type": "played", "id": N}   clip N finished or was stopped
    server -> page   text:   {"type": "ready"} | {"type": "busy"} | {"type": "stop"}
                             {"type": "user", "text": ..., "lang": ...}   what the caller said
                             {"type": "agent", "reply": N, "text": ...}   a sentence the agent is about to say
                             {"type": "order", "items": [...], "total": N} the order so far (not sent yet)
                     binary: 4-byte big-endian clip id, then a WAV file to play

The pipeline's threads are plain threads, so the asyncio server runs on its
own thread and everything crossing over goes through thread-safe calls.

The microphone is only available to a page on localhost or https, so serving
this to another machine needs TLS in front of it.
"""

import asyncio
import io
from html import escape as html_escape
import json
import logging
import os
import re
import struct
import threading
import time
import uuid
import wave
from http import HTTPStatus
from pathlib import Path

from websockets.asyncio.server import serve

from .shops import valid_name
from .transport import Capture, PlaybackTimeout, Transport

log = logging.getLogger("transport.websocket")

PAGE_PATH = Path(__file__).parent / "web" / "index.html"
SHOP_ROUTE = re.compile(r"^/s/(?P<shop>[^/]+)(?P<rest>/ws|/)?$")

# If nothing is reading the audio (no call detected yet), keep only the most
# recent 10 seconds rather than growing without bound.
MAX_BUFFER_BYTES = 16000 * 2 * 10

# How long past a clip's own length to wait for the page to confirm it played.
PLAY_GRACE_SEC = 5.0


def _wav_seconds(wav_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav_bytes)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 10.0


class _Session:
    """One browser call: the audio it has sent and the clips it still owes us."""

    def __init__(self, sid, ws, shop=None):
        self.id = sid
        self.ws = ws
        self.shop = shop
        self.started = time.monotonic()
        self.closed = threading.Event()
        self.lock = threading.Lock()
        self.pending = {}            # clip id -> Event set when the page confirms it
        self.next_id = 0
        self._cond = threading.Condition()
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        with self._cond:
            self._buf += data
            if len(self._buf) > MAX_BUFFER_BYTES:
                del self._buf[:len(self._buf) - MAX_BUFFER_BYTES]
            self._cond.notify_all()

    def read(self, size: int, timeout_sec: float) -> bytes:
        deadline = time.monotonic() + timeout_sec
        with self._cond:
            while len(self._buf) < size and not self.closed.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(remaining)
            n = min(size, len(self._buf))
            out = bytes(self._buf[:n])
            del self._buf[:n]
            return out

    def close(self) -> None:
        self.closed.set()
        with self._cond:
            self._cond.notify_all()
        with self.lock:
            events = list(self.pending.values())
        for ev in events:
            ev.set()


class _SessionCapture(Capture):
    def __init__(self, session):
        self._session = session

    def read_frame(self, size: int, timeout_sec: float) -> bytes:
        return self._session.read(size, timeout_sec)

    def close(self) -> None:
        pass   # the call's lifetime is the socket's, not the recorder's


class WebSocketTransport(Transport):
    name = "websocket"
    sample_rate = 16000
    poll_interval_sec = 0.25
    # The browser cancels the agent's echo (echoCancellation in getUserMedia),
    # so no extra mute after a clip. To be tuned against measurements.
    default_echo_tail_sec = 0.0
    default_greeting_delay_sec = 0.3

    def __init__(self, host: str | None = None, port: int | None = None):
        self.host = host or os.environ.get("AUDIO_HOST", "127.0.0.1")
        self.port = int(port if port is not None else os.environ.get("AUDIO_PORT", "8765"))
        self._loop = None
        self._stop = None
        self._thread = None
        self._ready = threading.Event()
        self._error = None
        self._session = None
        self._session_lock = threading.Lock()
        self._default_shop = None
        self._shop_exists = None        # callable(name) -> bool; None accepts any valid name
        self._shop_title = None         # callable(name) -> str shown on the call page
        self._http_handlers = []

    def configure(self, default_shop=None, shop_exists=None, shop_title=None) -> None:
        """Tell the server which shops exist and what to call them."""
        self._default_shop = default_shop
        self._shop_exists = shop_exists
        self._shop_title = shop_title

    def add_http_handler(self, handler) -> None:
        """handler(path, headers, remote_address) -> a Reply-like object, or None to pass."""
        self._http_handlers.append(handler)

    # -- lifecycle --------------------------------------------------------

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def describe(self) -> str:
        shop = self._default_shop
        base = f"{self.url}/s/{shop}/" if shop else f"{self.url}/"
        text = f"open {base} in a browser and press Start call"
        if shop and self._http_handlers:
            text += f" (shopkeeper dashboard: {base}dashboard)"
        return text

    def live_calls(self) -> list:
        s = self._session
        if s is None or s.closed.is_set():
            return []
        return [{"shop": s.shop or self._default_shop, "seconds": int(time.monotonic() - s.started)}]

    def call_shop(self):
        s = self._session
        return (s.shop or self._default_shop) if s is not None and not s.closed.is_set() else None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="web-transport")
        self._thread.start()
        if not self._ready.wait(10):
            raise RuntimeError("The call server did not start within 10 seconds.")
        if self._error is not None:
            raise RuntimeError(
                f"Could not start the call server on {self.host}:{self.port}: {self._error}. "
                f"Another copy may be running; set AUDIO_PORT to use a different port."
            )

    def _run(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as e:
            self._error = e
        finally:
            self._ready.set()

    async def _serve(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        async with serve(self._handle, self.host, self.port,
                         process_request=self._process_request, max_size=2 ** 20) as server:
            self.port = server.sockets[0].getsockname()[1]
            self._ready.set()
            await self._stop.wait()

    def close(self) -> None:
        if self._loop is not None and self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread is not None:
            self._thread.join(timeout=3)

    # -- the server (runs on its own thread) ------------------------------

    def _shop_ok(self, name) -> bool:
        if name is None:
            return True
        return valid_name(name) and (self._shop_exists is None or bool(self._shop_exists(name)))

    def _title(self, name) -> str:
        name = name or self._default_shop or "Dukaan Dost"
        if self._shop_title is not None:
            try:
                return self._shop_title(name)
            except Exception:
                pass
        return name.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _html(connection, status, text, content_type="text/html; charset=utf-8", extra=None):
        response = connection.respond(HTTPStatus(status), text)
        del response.headers["Content-Type"]
        response.headers["Content-Type"] = content_type
        response.headers["Cache-Control"] = "no-store"
        for key, value in (extra or {}).items():
            if key in response.headers:
                del response.headers[key]
            response.headers[key] = value
        return response

    def _process_request(self, connection, request):
        path = request.path.split("?", 1)[0]
        address = getattr(connection, "remote_address", None)
        remote = str(address[0]) if address else ""

        for handler in self._http_handlers:
            reply = handler(path, request.headers, remote)
            if reply is not None:
                return self._html(connection, reply.status, reply.body.decode("utf-8"),
                                  reply.content_type, reply.headers)

        shop, is_ws = None, False
        if path == "/ws":
            is_ws = True
        elif path in ("/", "/index.html"):
            pass
        else:
            m = SHOP_ROUTE.match(path)
            if m is None:
                return connection.respond(HTTPStatus.NOT_FOUND, "Not found.\n")
            shop, is_ws = m.group("shop"), m.group("rest") == "/ws"
        if not self._shop_ok(shop):
            return connection.respond(HTTPStatus.NOT_FOUND, "No such shop.\n")
        if is_ws:
            return None                                       # carry on with the WebSocket handshake
        try:
            body = PAGE_PATH.read_text(encoding="utf-8")
        except OSError:
            return connection.respond(HTTPStatus.INTERNAL_SERVER_ERROR, "The call page is missing.\n")
        return self._html(connection, 200, body.replace("{{SHOP}}", html_escape(self._title(shop))))

    async def _handle(self, ws) -> None:
        m = SHOP_ROUTE.match(ws.request.path.split("?", 1)[0])
        shop = m.group("shop") if m else None
        with self._session_lock:
            current = self._session
            if current is not None and not current.closed.is_set():
                busy = True
            else:
                busy = False
                session = _Session(f"web-{uuid.uuid4().hex[:8]}", ws, shop or self._default_shop)
                self._session = session
        if busy:
            await ws.send(json.dumps({"type": "busy"}))
            await ws.close(1013, "a call is already in progress")
            return

        log.info(f"[CALL] browser connected: {session.id} (shop: {session.shop or 'default'})")
        try:
            await ws.send(json.dumps({"type": "ready", "sample_rate": self.sample_rate}))
            async for message in ws:
                if isinstance(message, (bytes, bytearray)):
                    session.feed(bytes(message))
                    continue
                try:
                    data = json.loads(message)
                except ValueError:
                    continue
                if data.get("type") == "played":
                    with session.lock:
                        ev = session.pending.get(data.get("id"))
                    if ev is not None:
                        ev.set()
        except Exception as e:
            log.debug(f"[CALL] socket ended: {e}")
        finally:
            session.close()
            log.info(f"[CALL] browser disconnected: {session.id}")

    # -- the Transport interface (called from the pipeline's threads) -----

    def _send(self, session, payload) -> bool:
        """Send from any thread. False if the socket is gone."""
        if self._loop is None:
            return False
        try:
            asyncio.run_coroutine_threadsafe(session.ws.send(payload), self._loop).result(timeout=5)
            return True
        except Exception as e:
            log.debug(f"[CALL] send failed: {e}")
            return False

    def send_event(self, event: dict) -> None:
        s = self._session
        if s is None or s.closed.is_set() or self._loop is None:
            return
        try:                                               # fire and forget: a slow page must never stall the pipeline
            asyncio.run_coroutine_threadsafe(s.ws.send(json.dumps(event)), self._loop)
        except Exception as e:
            log.debug(f"[CALL] event not sent: {e}")

    def find_call(self):
        s = self._session
        if s is not None and not s.closed.is_set():
            return s.id, s.id
        return None, None

    def device_name(self) -> str:
        return "browser"

    def open_capture(self, key: str) -> Capture:
        s = self._session
        if s is None or s.id != key:
            closed = _Session("none", None)
            closed.close()
            return _SessionCapture(closed)
        return _SessionCapture(s)

    def play(self, key: str, wav_bytes: bytes, timeout_sec: float) -> None:
        s = self._session
        if s is None or s.id != key or s.closed.is_set():
            return                                         # the call has gone; nothing to play to
        ev = threading.Event()
        with s.lock:
            clip_id = s.next_id
            s.next_id += 1
            s.pending[clip_id] = ev
        try:
            if not self._send(s, struct.pack(">I", clip_id) + wav_bytes):
                return
            limit = min(timeout_sec, _wav_seconds(wav_bytes) + PLAY_GRACE_SEC)
            if not ev.wait(limit):
                raise PlaybackTimeout(f"the page did not confirm clip {clip_id} within {limit:.1f}s")
        finally:
            with s.lock:
                s.pending.pop(clip_id, None)

    def stop_playback(self) -> bool:
        s = self._session
        if s is None:
            return False
        with s.lock:
            events = list(s.pending.values())
        if not events:
            return False
        self._send(s, json.dumps({"type": "stop"}))
        for ev in events:
            ev.set()
        return True
