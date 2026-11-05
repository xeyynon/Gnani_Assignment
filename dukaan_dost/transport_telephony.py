"""
transport_telephony.py

A real phone number for the agent (DEC-046). A telephony provider answers the call and streams the caller's audio to
this server over a WebSocket, and plays back whatever audio the server sends. It is the browser transport's twin:
same server, same one-call-at-a-time session, same pipeline above it; only the framing of the audio differs.

    AUDIO_TRANSPORT=telephony
    TELEPHONY_TOKEN=<a long random secret>       # required; with none set every call is refused
    wss://<public host>/telephony/twilio         # point a Twilio <Connect><Stream> at this
    wss://<public host>/telephony/exotel         # point an Exotel Voicebot applet at this (add ?sample-rate=16000)

Two adapters, one per provider, translate its messages (checked against the providers' documentation on 2026-11-03):
  Twilio   JSON events connected, start, media, mark, stop, dtmf; audio is base64 mu-law, 8 kHz, mono; we send media,
           mark (Twilio returns it when the audio before it has played) and clear (drops buffered audio: barge-in).
  Exotel   JSON events connected, start, media, mark, stop, dtmf; audio is base64 raw 16-bit little-endian PCM at 8000,
           16000 or 24000 Hz; outbound chunks must be 3200 to 100000 bytes in multiples of 320; mark and clear as above.

Not tested against a real provider: no account exists yet (KYC, B-39). The tests run a stand-in provider that follows
the documented messages.

Privacy: the caller's phone number arrives in the start message. It is never stored or logged here.

The token and the shop come from the start message's custom parameters (Twilio does not allow a query string on the
stream URL) or, failing that, from the URL's query string. Without the right token the socket is closed at once.
"""

import asyncio
import base64
import hmac
import io
import json
import logging
import os
import threading
import uuid
import wave
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

import numpy as np

from .shops import valid_name
from .transport import PlaybackTimeout
from .transport_websocket import PLAY_GRACE_SEC, WebSocketTransport, _Session, _wav_seconds

log = logging.getLogger("transport_telephony")

PIPELINE_RATE = 16000
MIN_TOKEN_CHARS = 16
TWILIO_CHUNK_BYTES = 4000            # mu-law bytes per outbound message (0.5 s); Twilio accepts any size
EXOTEL_CHUNK_BYTES = 9600            # 300 ms at 16 kHz; within 3200..100000 and a multiple of 320
EXOTEL_MIN_CHUNK = 3200
EXOTEL_UNIT = 320


# ---------------------------------------------------------------------------------------------------------------------
# Audio conversion (plain numpy: the standard library's audioop is gone in Python 3.13)
# ---------------------------------------------------------------------------------------------------------------------

_BIAS, _CLIP = 0x84, 32635


def mulaw_encode(pcm: np.ndarray) -> bytes:
    """16-bit PCM samples to G.711 mu-law bytes."""
    x = np.asarray(pcm, dtype=np.int32)
    sign = np.where(x < 0, 0x80, 0)
    x = np.minimum(np.abs(x), _CLIP) + _BIAS
    exponent = np.floor(np.log2(x)).astype(np.int32) - 7
    mantissa = (x >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa) & 0xFF).astype(np.uint8).tobytes()


def mulaw_decode(data: bytes) -> np.ndarray:
    """G.711 mu-law bytes to 16-bit PCM samples."""
    u = ~np.frombuffer(data, dtype=np.uint8).astype(np.int32) & 0xFF
    sign = u & 0x80
    exponent = (u >> 4) & 0x07
    mantissa = u & 0x0F
    sample = (((mantissa << 3) + _BIAS) << exponent) - _BIAS
    return np.where(sign != 0, -sample, sample).astype(np.int16)


def resample(pcm: np.ndarray, src: int, dst: int) -> np.ndarray:
    """Plain resampling by linear interpolation, after averaging when the rate goes down a lot. Neural restoration
    made Hindi speech recognition worse (method M8), so nothing cleverer is done."""
    x = np.asarray(pcm, dtype=np.float32)
    if src == dst or len(x) == 0:
        return x.astype(np.int16)
    if src >= 2 * dst:
        k = src // dst
        x = x[: len(x) // k * k].reshape(-1, k).mean(axis=1)
        src //= k
    n_out = int(round(len(x) * dst / src))
    positions = np.arange(n_out) * (src / dst)
    out = np.interp(positions, np.arange(len(x)), x)
    return np.clip(out, -32768, 32767).astype(np.int16)


# ---------------------------------------------------------------------------------------------------------------------
# The two providers
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Event:
    kind: str                                  # connected | start | media | mark | stop | dtmf
    stream_sid: str = ""
    pcm: bytes = b""                           # inbound audio already at 16 kHz, for "media"
    params: dict = field(default_factory=dict)  # custom parameters, for "start"
    name: str = ""                             # the label, for "mark"
    reason: str = ""


def _json(raw):
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _b64(payload) -> bytes:
    try:
        return base64.b64decode(payload or "", validate=False)
    except Exception:
        return b""


class TwilioAdapter:
    name = "twilio"

    def parse(self, raw):
        d = _json(raw)
        if d is None:
            return None
        kind = d.get("event")
        if kind == "start":
            start = d.get("start") or {}
            return Event("start", stream_sid=str(start.get("streamSid") or d.get("streamSid") or ""),
                         params=dict(start.get("customParameters") or {}))
        if kind == "media":
            media = d.get("media") or {}
            if media.get("track", "inbound") != "inbound":
                return None
            pcm8 = mulaw_decode(_b64(media.get("payload")))
            return Event("media", stream_sid=str(d.get("streamSid") or ""), pcm=resample(pcm8, 8000, PIPELINE_RATE).tobytes())
        if kind == "mark":
            return Event("mark", name=str((d.get("mark") or {}).get("name") or ""))
        if kind == "stop":
            return Event("stop")
        if kind in ("connected", "dtmf"):
            return Event(kind)
        return None

    def media_out(self, stream_sid, pcm16k: bytes) -> list:
        pcm8 = resample(np.frombuffer(pcm16k, dtype=np.int16), PIPELINE_RATE, 8000)
        data = mulaw_encode(pcm8)
        return [json.dumps({"event": "media", "streamSid": stream_sid,
                            "media": {"payload": base64.b64encode(data[i:i + TWILIO_CHUNK_BYTES]).decode("ascii")}})
                for i in range(0, len(data), TWILIO_CHUNK_BYTES)]

    def mark_msg(self, stream_sid, name):
        return json.dumps({"event": "mark", "streamSid": stream_sid, "mark": {"name": name}})

    def clear_msg(self, stream_sid):
        return json.dumps({"event": "clear", "streamSid": stream_sid})


class ExotelAdapter:
    name = "exotel"

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate            # what we ask Exotel for; the start message says what it really uses

    def parse(self, raw):
        d = _json(raw)
        if d is None:
            return None
        kind = d.get("event")
        if kind == "start":
            start = d.get("start") or {}
            fmt = start.get("media_format") or {}
            try:
                self.sample_rate = int(fmt.get("sample_rate") or self.sample_rate)
            except (TypeError, ValueError):
                pass
            return Event("start", stream_sid=str(d.get("stream_sid") or start.get("stream_sid") or ""),
                         params=dict(start.get("custom_parameters") or {}))
        if kind == "media":
            media = d.get("media") or {}
            raw_pcm = _b64(media.get("payload"))
            raw_pcm = raw_pcm[: len(raw_pcm) // 2 * 2]
            pcm = resample(np.frombuffer(raw_pcm, dtype=np.int16), self.sample_rate, PIPELINE_RATE)
            return Event("media", stream_sid=str(d.get("stream_sid") or ""), pcm=pcm.tobytes())
        if kind == "mark":
            return Event("mark", name=str((d.get("mark") or {}).get("name") or ""))
        if kind == "stop":
            return Event("stop", reason=str((d.get("stop") or {}).get("reason") or ""))
        if kind in ("connected", "dtmf"):
            return Event(kind)
        return None

    def media_out(self, stream_sid, pcm16k: bytes) -> list:
        pcm = resample(np.frombuffer(pcm16k, dtype=np.int16), PIPELINE_RATE, self.sample_rate).tobytes()
        step = (EXOTEL_CHUNK_BYTES // EXOTEL_UNIT) * EXOTEL_UNIT
        messages = []
        for i in range(0, len(pcm), step):
            chunk = pcm[i:i + step]
            target = max(EXOTEL_MIN_CHUNK, -(-len(chunk) // EXOTEL_UNIT) * EXOTEL_UNIT)      # multiple of 320, at least 3200
            chunk = chunk + b"\x00" * (target - len(chunk))
            messages.append(json.dumps({"event": "media", "stream_sid": stream_sid,
                                        "media": {"payload": base64.b64encode(chunk).decode("ascii")}}))
        return messages

    def mark_msg(self, stream_sid, name):
        return json.dumps({"event": "mark", "stream_sid": stream_sid, "mark": {"name": name}})

    def clear_msg(self, stream_sid):
        return json.dumps({"event": "clear", "stream_sid": stream_sid})


# ---------------------------------------------------------------------------------------------------------------------
# The transport
# ---------------------------------------------------------------------------------------------------------------------

def _token_ok(given: str, wanted: str) -> bool:
    return len(wanted) >= MIN_TOKEN_CHARS and hmac.compare_digest(str(given or "").encode(), wanted.encode())


class TelephonyTransport(WebSocketTransport):
    """The browser transport plus phone-provider sockets. Browser calls still work on the same server."""

    name = "telephony"
    # A phone network cancels most echo itself, and the self-echo filter dropped real callers who repeat an item the
    # agent just said (B-36), so no extra mute and no filter by default. SELF_ECHO_FILTER=1 turns the filter on.
    default_echo_tail_sec = 0.0

    def __init__(self, host=None, port=None, token: str | None = None):
        super().__init__(host, port)
        self._token = token if token is not None else os.environ.get("TELEPHONY_TOKEN", "")
        self.add_ws_handler("/telephony/twilio", lambda ws: self._phone(ws, TwilioAdapter()))
        self.add_ws_handler("/telephony/exotel", lambda ws: self._phone(ws, ExotelAdapter(_rate_from_query(ws))))
        if len(self._token) < MIN_TOKEN_CHARS:
            log.warning(f"[PHONE] TELEPHONY_TOKEN is missing or shorter than {MIN_TOKEN_CHARS} characters: every phone "
                        f"call will be refused until a long random secret is set.")

    @staticmethod
    def _query(ws) -> dict:
        return {k: v[0] for k, v in parse_qs(urlsplit(ws.request.path).query).items()}

    def describe(self) -> str:
        return (f"phone providers connect to wss://<public host>/telephony/twilio or /telephony/exotel "
                f"(local port {self.port}); a browser can still open {self.url}/")

    # ---- one phone call ---------------------------------------------------------------------------------------------

    async def _phone(self, ws, adapter) -> None:
        session = None
        query = self._query(ws)
        try:
            async for raw in ws:
                if isinstance(raw, (bytes, bytearray)):
                    continue
                event = adapter.parse(raw)
                if event is None:
                    continue
                if event.kind == "start" and session is None:
                    session = await self._begin(ws, adapter, event, query)
                    if session is None:
                        return
                elif event.kind == "media" and session is not None and event.pcm:
                    session.feed(event.pcm)
                elif event.kind == "mark" and session is not None:
                    self._mark_arrived(session, event.name)
                elif event.kind == "stop":
                    break
        except Exception as e:
            log.debug(f"[PHONE] socket ended: {e}")
        finally:
            if session is not None:
                session.close()
                log.info(f"[PHONE] call ended: {session.id}")

    async def _begin(self, ws, adapter, event, query):
        token = event.params.get("token") or query.get("token") or ""
        if not _token_ok(token, self._token):
            log.warning(f"[PHONE] refused a {adapter.name} connection: wrong or missing token")
            await ws.close(1008, "not authorised")
            return None
        shop = str(event.params.get("shop") or query.get("shop") or "") or None
        if shop is not None and not self._shop_ok(shop):
            log.warning(f"[PHONE] refused a {adapter.name} connection: unknown shop")
            await ws.close(1008, "unknown shop")
            return None
        with self._session_lock:
            current = self._session
            if current is not None and not current.closed.is_set():
                busy = True
            else:
                busy = False
                session = _Session(f"phone-{uuid.uuid4().hex[:8]}", ws, shop or self._default_shop)
                session.adapter, session.stream_sid = adapter, event.stream_sid
                self._session = session
        if busy:
            await ws.close(1013, "a call is already in progress")
            return None
        log.info(f"[PHONE] {adapter.name} call connected: {session.id} (shop: {session.shop or 'default'})")
        return session

    @staticmethod
    def _mark_arrived(session, name: str) -> None:
        try:
            clip_id = int(str(name).rsplit("-", 1)[-1])
        except ValueError:
            return
        with session.lock:
            ev = session.pending.get(clip_id)
        if ev is not None:
            ev.set()

    # ---- the Transport interface for phone sessions ----------------------------------------------------------------------

    def play(self, key: str, wav_bytes: bytes, timeout_sec: float) -> None:
        s = self._session
        adapter = getattr(s, "adapter", None) if s is not None else None
        if adapter is None:
            return super().play(key, wav_bytes, timeout_sec)
        if s.id != key or s.closed.is_set():
            return
        with wave.open(io.BytesIO(wav_bytes)) as w:
            pcm = w.readframes(w.getnframes())
        ev = threading.Event()
        with s.lock:
            clip_id = s.next_id
            s.next_id += 1
            s.pending[clip_id] = ev
        try:
            for message in adapter.media_out(s.stream_sid, pcm):
                if not self._send(s, message):
                    return
            if not self._send(s, adapter.mark_msg(s.stream_sid, f"{s.id}-{clip_id}")):
                return
            limit = min(timeout_sec, _wav_seconds(wav_bytes) + PLAY_GRACE_SEC)
            if not ev.wait(limit):
                raise PlaybackTimeout(f"the provider did not confirm clip {clip_id} within {limit:.1f}s")
        finally:
            with s.lock:
                s.pending.pop(clip_id, None)

    def stop_playback(self) -> bool:
        s = self._session
        adapter = getattr(s, "adapter", None) if s is not None else None
        if adapter is None:
            return super().stop_playback()
        with s.lock:
            events = list(s.pending.values())
        if not events:
            return False
        self._send(s, adapter.clear_msg(s.stream_sid))
        for ev in events:
            ev.set()
        return True


def _rate_from_query(ws) -> int:
    """The sample rate Exotel was told to use (?sample-rate=16000), 16000 if absent or odd."""
    try:
        rate = int(parse_qs(urlsplit(ws.request.path).query).get("sample-rate", ["16000"])[0])
    except ValueError:
        return 16000
    return rate if rate in (8000, 16000, 24000) else 16000
