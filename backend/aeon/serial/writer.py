"""
aeon/serial/writer.py — Outbound COMMAND frame writer.

Builds and sends AEON protocol COMMAND frames (type 0x10) to the Arduino
via the serial transport exposed by SerialBridge.

Used by the PolicyEngine to send actuation commands (relay, LED, buzzer)
and by the DeviceRegistry to send heartbeat pings.
"""

from __future__ import annotations

import struct
import structlog
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import StreamWriter
    from fastapi import WebSocket

log = structlog.get_logger(__name__)

# CRC-16/CCITT-FALSE: poly=0x1021, init=0xFFFF
def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


class CommandType:
    """Arduino-side command type codes."""
    RELAY_SET     = 0x01
    LED_SET       = 0x02
    BUZZER        = 0x03
    CHECKPOINT    = 0x04   # force EEPROM checkpoint
    REBOOT        = 0x05
    CONFIG_UPDATE = 0x06


class SerialWriter:
    """
    Sends COMMAND JSON payloads to the Arduino over the WebSocket transport.

    The writer is injected with a WebSocket reference from the Gateway
    once the connection is established.
    """

    def __init__(self) -> None:
        self._sockets: list[WebSocket] = []
        self._seq: int = 0
        self._lock = asyncio.Lock()
        self._commands_sent: int = 0

    def attach(self, websocket: WebSocket) -> None:
        """Called by Gateway when a WebSocket connection opens."""
        if websocket not in self._sockets:
            self._sockets.append(websocket)
        log.info("serial_writer.attached", clients=len(self._sockets))

    def detach(self, websocket: WebSocket) -> None:
        """Called by Gateway when a WebSocket connection drops."""
        if websocket in self._sockets:
            self._sockets.remove(websocket)
        log.info("serial_writer.detached", clients=len(self._sockets))

    @property
    def is_connected(self) -> bool:
        return len(self._sockets) > 0

    @property
    def commands_sent(self) -> int:
        return self._commands_sent

    async def send_json(self, payload: dict) -> bool:
        """
        Build and send a JSON string to all connected Arduino gateways.
        Returns True on success, False if no connections.
        """
        if not self._sockets:
            log.warning("serial_writer.not_connected — command dropped", typ=payload.get("typ"))
            return False

        async with self._lock:
            self._seq += 1
            payload["seq"] = self._seq
            
            import json
            json_str = json.dumps(payload) + "\n"

            success_count = 0
            for ws in self._sockets:
                try:
                    await ws.send_text(json_str)
                    success_count += 1
                except Exception:
                    log.exception("serial_writer.send_error")

            if success_count > 0:
                self._commands_sent += 1
                log.debug("serial_writer.sent", typ=payload.get("typ"), seq=self._seq)
                return True
            return False

    async def send_relay(self, relay_id: int, state: bool) -> bool:
        """Set a relay on/off."""
        return await self.send_json({
            "typ": "relay_set",
            "relay": relay_id,
            "state": state
        })

    async def send_buzzer(self, duration_ms: int = 200) -> bool:
        """Trigger a buzzer for duration_ms."""
        return await self.send_json({
            "typ": "buzzer",
            "duration": duration_ms
        })

    async def send_checkpoint(self) -> bool:
        """Force an immediate EEPROM checkpoint."""
        return await self.send_json({
            "typ": "checkpoint"
        })

    async def send_policy_update(self, theta: float, cmd_id: str) -> bool:
        return await self.send_json({
            "typ": "policy_update",
            "theta": round(theta, 2),
            "command_id": cmd_id
        })

    async def send_model_update(self, model_v: int, mean: float, std: float, theta: float, cmd_id: str) -> bool:
        return await self.send_json({
            "typ": "model_update",
            "model_v": model_v,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "theta": round(theta, 2),
            "command_id": cmd_id
        })
