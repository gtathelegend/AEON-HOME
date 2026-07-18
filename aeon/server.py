"""WebSocket hub + static server.

Serves two screens from one process:
  /            the PC dashboard  (full control view)
  /phone       the phone client  (personal view, mic + one-tap answers)

Both read the same HubState, so they never disagree. The phone posts commands in
over the same socket; in Phase 1 they drive the scripted house, in Phase 2 they
are signed and routed to the real central node.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class Broadcaster:
    """Fan a snapshot out to every connected screen."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def add(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)

    async def drop(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def send(self, message: dict) -> None:
        async with self._lock:
            targets = list(self._clients)
        if not targets:
            return
        payload = json.dumps(message)
        dead = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    @property
    def count(self) -> int:
        return len(self._clients)


def lan_ip() -> str:
    """The address to open on the phone. No packet is actually sent."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def create_app(source) -> FastAPI:
    """`source` drives the house. It must expose:

        state            -> HubState
        async run(bcast) -> long-running loop
        async on_message(msg, bcast) -> handle a message from a screen
    """
    app = FastAPI(title="AEON Home")
    bcast = Broadcaster()
    app.state.source = source
    app.state.bcast = bcast

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.task = asyncio.create_task(source.run(bcast))

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        app.state.task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await app.state.task

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        await bcast.add(ws)
        try:
            # A new screen gets the whole world immediately, not on the next tick.
            await ws.send_text(json.dumps(source.state.snapshot()))
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await source.on_message(msg, bcast)
        except WebSocketDisconnect:
            pass
        finally:
            await bcast.drop(ws)

    @app.get("/")
    async def dashboard() -> FileResponse:
        return FileResponse(WEB_DIR / "dashboard.html")

    @app.get("/phone")
    async def phone() -> FileResponse:
        return FileResponse(WEB_DIR / "phone.html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app
