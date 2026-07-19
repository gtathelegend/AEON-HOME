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

from . import discovery
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class Broadcaster:
    """Fan a snapshot out to every connected screen."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        # Which of them are phones. The dashboard reports this, so a presenter
        # can see the handset is actually attached before speaking into it --
        # rather than discovering the socket never connected mid-demo.
        self._phones: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def add(self, ws: WebSocket, kind: str = "screen") -> None:
        async with self._lock:
            self._clients.add(ws)
            if kind == "phone":
                self._phones.add(ws)

    async def drop(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
            self._phones.discard(ws)

    @property
    def phones(self) -> int:
        return len(self._phones)

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


def create_app(source, port: int = 8800) -> FastAPI:
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
        # Answer "where is the hub?" so the phone never asks a person for an IP.
        # Optional by construction: if the port is busy the hub runs regardless
        # and the app falls back to its baked-in address.
        app.state.discovery, _ = await discovery.serve(hub_port=port)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        if getattr(app.state, "discovery", None) is not None:
            app.state.discovery.close()
        app.state.task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await app.state.task

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        peer = ws.client.host if ws.client else "?"
        await ws.accept()
        # `?client=phone` marks a handset. The native Android app and the web
        # phone client both send it; anything else counts as a screen.
        kind = ws.query_params.get("client", "screen")
        await bcast.add(ws, kind)
        source.state.phones = bcast.phones
        # Logged with the peer address. "Nothing appears here when I press the
        # mic" and "it connects then drops" are different faults with different
        # fixes, and without this line they look the same from the phone.
        print(f"  [ws] {kind} connected from {peer} "
              f"(screens={bcast.count}, phones={bcast.phones})", flush=True)
        try:
            # A new screen gets the whole world immediately, not on the next tick.
            await ws.send_text(json.dumps(source.state.snapshot()))
            if kind == "phone":
                source.state.event("phone", text="a phone connected")
                await bcast.send(source.state.snapshot())
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if kind == "phone":
                    print(f"  [ws] {peer} -> {json.dumps(msg)[:160]}", flush=True)
                await source.on_message(msg, bcast)
        except WebSocketDisconnect:
            pass
        except Exception as exc:                        # noqa: BLE001
            print(f"  [ws] {kind} {peer} error: {type(exc).__name__}: {exc}",
                  flush=True)
        finally:
            await bcast.drop(ws)
            source.state.phones = bcast.phones
            print(f"  [ws] {kind} from {peer} disconnected "
                  f"(screens={bcast.count}, phones={bcast.phones})", flush=True)
            if kind == "phone":
                source.state.event("phone", text="the phone disconnected")
                with contextlib.suppress(Exception):
                    await bcast.send(source.state.snapshot())

    @app.get("/")
    async def dashboard() -> FileResponse:
        return FileResponse(WEB_DIR / "dashboard.html")

    @app.get("/phone")
    async def phone() -> FileResponse:
        return FileResponse(WEB_DIR / "phone.html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app
