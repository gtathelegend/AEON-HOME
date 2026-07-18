"""A leaf device: a dumb WiFi actuator.

No model, no NPU, no ONNX runtime. It only has to switch a load. In the demo
these run as TCP servers on loopback; on real hardware each is a ~200-rupee
ESP32 with a relay, speaking exactly this protocol.

It verifies the HMAC before acting. This is not ceremony -- a leaf switches a
real appliance, and an unsigned command on the home WiFi is how a neighbour
turns your AC on at three in the morning.
"""

from __future__ import annotations

import asyncio
import json

from . import devices, protocol


class LeafDevice:
    def __init__(self, device_id: str, host: str = "127.0.0.1", port: int = 0) -> None:
        self.device_id = device_id
        self.spec = devices.get(device_id)
        self.host = host
        self.port = port

        self.on = False
        self.level: float | None = None
        self.applied_count = 0
        self.rejected_count = 0

        self._server: asyncio.AbstractServer | None = None
        self._writers: set[asyncio.StreamWriter] = set()

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        """Unplug the bulb.

        Closing the server only stops it accepting NEW connections; sockets
        already established keep working. A node holding a persistent connection
        could therefore go on switching a device that was supposedly unplugged.
        Pulling power kills every socket, so this does too.
        """
        if self._server is None:
            return

        self._server.close()
        try:
            await self._server.wait_closed()
        except Exception:
            pass
        self._server = None

        for writer in list(self._writers):
            try:
                writer.close()
            except Exception:
                pass
        self._writers.clear()

    @property
    def online(self) -> bool:
        return self._server is not None

    async def _handle(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        self._writers.add(writer)
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                if self._server is None:
                    break                      # unplugged mid-connection
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                response = self._apply(msg)
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self._writers.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    def _apply(self, msg: dict) -> dict:
        # Verify before acting, always.
        if not protocol.verify(msg):
            self.rejected_count += 1
            return protocol.reject("bad signature")

        if msg.get("typ") != "actuate":
            return protocol.reject("unsupported message type")

        if msg.get("device") != self.device_id:
            return protocol.reject("wrong device")

        on = bool(msg.get("on"))
        level = msg.get("level")
        if on and level is not None:
            # Clamp at the actuator. The node should never send out-of-range,
            # but a relay that trusts its input is a relay that melts something.
            level = max(self.spec.lo, min(self.spec.hi, float(level)))

        changed = (on != self.on) or (level != self.level)
        self.on = on
        self.level = level if on else None
        self.applied_count += 1

        return protocol.leaf_ack(self.device_id, self.on, self.level, changed)

    def snapshot(self) -> dict:
        return {
            "device": self.device_id,
            "on": self.on,
            "level": self.level,
            "online": self.online,
            "applied": self.applied_count,
            "rejected": self.rejected_count,
        }
