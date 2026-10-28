"""
transport_websocket.py

The call transport: a web page in a browser is the "phone". The page captures
the microphone, resamples it to 16 kHz and streams it over a WebSocket; the
agent's replies come back the same way and the page plays them. Nothing but
Python and a browser is needed (DEC-032).

One small server (the `websockets` package) does both jobs on one port:
    GET /      the call page (dukaan_dost/web/index.html)
    WS  /ws    the call itself

Protocol (one call at a time; a second visitor is told "busy"):
    page -> server   binary: 16 kHz mono s16le PCM, any chunk size
                     text:   {"type": "played", "id": N}   clip N finished or was stopped
    server -> page   text:   {"type": "ready"} | {"type": "busy"} | {"type": "stop"}
                     binary: 4-byte big-endian clip id, then a WAV file to play

The pipeline's threads are plain threads, so the asyncio server runs on its
own thread and everything crossing over goes through thread-safe calls.

The microphone is only available to a page on localhost or https, so serving
this to another machine needs TLS in front of it.
"""

import asyncio
import io
import json
import logging
import os
import struct
import threading
import time
import uuid
import wave
from http import HTTPStatus
from pathlib import Path

from websockets.asyncio.server import serve

from .transport import Capture, PlaybackTimeout, Transport

log = logging.getLogger("transport.websocket")

PAGE_PATH = Path(__file__).parent / "web" / "index.html"

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

    def __init__(self, sid, ws):
        self.id = sid
        self.ws = ws
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

    # -- lifecycle --------------------------------------------------------

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def describe(self) -> str:
        return f"open {self.url} in a browser and press Start call"

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

    def _process_request(self, connection, request):
        path = request.path.split("?", 1)[0]
        if path == "/ws":
            return None                                   # carry on with the WebSocket handshake
        if path in ("/", "/index.html"):
            try:
                body = PAGE_PATH.read_text(encoding="utf-8")
            except OSError:
                return connection.respond(HTTPStatus.INTERNAL_SERVER_ERROR, "The call page is missing.\n")
            response = connection.respond(HTTPStatus.OK, body)
            del response.headers["Content-Type"]
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            response.headers["Cache-Control"] = "no-store"
            return response
        return connection.respond(HTTPStatus.NOT_FOUND, "Not found.\n")

    async def _handle(self, ws) -> None:
        with self._session_lock:
            current = self._session
            if current is not None and not current.closed.is_set():
                busy = True
            else:
                busy = False
                session = _Session(f"web-{uuid.uuid4().hex[:8]}", ws)
                self._session = session
        if busy:
            await ws.send(json.dumps({"type": "busy"}))
            await ws.close(1013, "a call is already in progress")
            return

        log.info(f"[CALL] browser connected: {session.id}")
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
