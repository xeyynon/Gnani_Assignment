"""
A small WebSocket server run in a background thread, for testing the Gnani
backends without a key or a network. The handler is an async function taking
the connection; `server.url` is where to point the client.
"""

import asyncio
import threading

from websockets.asyncio.server import serve


class FakeServer:
    def __init__(self, handler):
        self._handler = handler
        self._loop = None
        self._stop = None
        self._ready = threading.Event()
        self.port = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self._thread.start()
        assert self._ready.wait(5), "fake server did not start"
        return self

    def __exit__(self, *exc):
        self._loop.call_soon_threadsafe(self._stop.set)
        self._thread.join(timeout=5)

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self.port}"

    def _run(self):
        asyncio.run(self._main())

    async def _main(self):
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        async with serve(self._handler, "127.0.0.1", 0) as server:
            self.port = server.sockets[0].getsockname()[1]
            self._ready.set()
            await self._stop.wait()
