# platform/communication/serial.py

from __future__ import annotations

import asyncio
import struct
import structlog
from datetime import datetime, timezone
from enum import IntEnum
from typing import TYPE_CHECKING, Optional, Union, Callable, Awaitable, Any

import serial_asyncio
from shared.types import FeatureFrame, AeonEvent
from shared.constants import (
    AEON_MAGIC,
    AEON_TYPE_FEATURE_FRAME,
    AEON_TYPE_EVENT,
    AEON_TYPE_COMMAND,
    AEON_TYPE_ACK,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

log = structlog.get_logger(__name__)

FrameCallback = Callable[[FeatureFrame], Awaitable[None]]
EventCallback = Callable[[AeonEvent], Awaitable[None]]


class FrameType(IntEnum):
    FEATURE_FRAME = AEON_TYPE_FEATURE_FRAME
    EVENT         = AEON_TYPE_EVENT
    COMMAND       = AEON_TYPE_COMMAND
    ACK           = AEON_TYPE_ACK


class _State(IntEnum):
    MAGIC0 = 0
    MAGIC1 = 1
    TYPE   = 2
    SEQ    = 3
    LEN    = 4
    PAYLOAD = 5
    CRC    = 6


class FrameParser:
    """
    Feed one byte at a time via feed().
    Returns a FeatureFrame, AeonEvent, or None when a complete frame is decoded.
    """

    MAGIC = AEON_MAGIC

    def __init__(self) -> None:
        self._state    = _State.MAGIC0
        self._type:    int = 0
        self._seq_buf  = bytearray(4)
        self._len_buf  = bytearray(2)
        self._seq_pos  = 0
        self._len_pos  = 0
        self._seq:     int = 0
        self._length:  int = 0
        self._payload  = bytearray()
        self._crc_pos  = 0

    def feed(self, byte: int) -> Optional[Union[FeatureFrame, AeonEvent]]:
        s = self._state

        if s == _State.MAGIC0:
            if byte == self.MAGIC[0]:
                self._state = _State.MAGIC1

        elif s == _State.MAGIC1:
            self._state = _State.TYPE if byte == self.MAGIC[1] else _State.MAGIC0

        elif s == _State.TYPE:
            self._type = byte
            self._seq_pos = 0
            self._state = _State.SEQ

        elif s == _State.SEQ:
            self._seq_buf[self._seq_pos] = byte
            self._seq_pos += 1
            if self._seq_pos == 4:
                self._seq = struct.unpack_from("<I", self._seq_buf)[0]
                self._len_pos = 0
                self._state = _State.LEN

        elif s == _State.LEN:
            self._len_buf[self._len_pos] = byte
            self._len_pos += 1
            if self._len_pos == 2:
                self._length = struct.unpack_from("<H", self._len_buf)[0]
                self._payload = bytearray()
                self._state = _State.PAYLOAD if self._length > 0 else _State.CRC

        elif s == _State.PAYLOAD:
            self._payload.append(byte)
            if len(self._payload) == self._length:
                self._crc_pos = 0
                self._state = _State.CRC

        elif s == _State.CRC:
            self._crc_pos += 1
            if self._crc_pos == 2:
                self._state = _State.MAGIC0
                return self._dispatch()

        return None

    def _dispatch(self) -> Optional[Union[FeatureFrame, AeonEvent]]:
        t = FrameType(self._type) if self._type in FrameType._value2member_map_ else None
        if t == FrameType.FEATURE_FRAME:
            try:
                return FeatureFrame.from_bytes(bytes(self._payload), self._seq)
            except struct.error:
                return None
        if t == FrameType.EVENT:
            raw = self._payload.decode("ascii", errors="replace")
            parts = raw.split(":", 2)
            category = parts[0] if len(parts) > 0 else ""
            name     = parts[1] if len(parts) > 1 else ""
            arg      = int(parts[2]) if len(parts) > 2 else 0
            return AeonEvent(category=category, name=name, arg=arg, seq=self._seq)
        return None


class CommandType:
    """Arduino-side command type codes."""
    RELAY_SET     = 0x01
    LED_SET       = 0x02
    BUZZER        = 0x03
    CHECKPOINT    = 0x04
    REBOOT        = 0x05
    CONFIG_UPDATE = 0x06


class SerialWriter:
    """
    Sends COMMAND JSON payloads to the Arduino over the WebSocket transport.
    """

    def __init__(self) -> None:
        self._sockets: list[WebSocket] = []
        self._seq: int = 0
        self._lock = asyncio.Lock()
        self._commands_sent: int = 0

    def attach(self, websocket: WebSocket) -> None:
        if websocket not in self._sockets:
            self._sockets.append(websocket)
        log.info("serial_writer.attached", clients=len(self._sockets))

    def detach(self, websocket: WebSocket) -> None:
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
        return await self.send_json({
            "typ": "relay_set",
            "relay": relay_id,
            "state": state
        })

    async def send_buzzer(self, duration_ms: int = 200) -> bool:
        return await self.send_json({
            "typ": "buzzer",
            "duration": duration_ms
        })

    async def send_checkpoint(self) -> bool:
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


class SerialBridge:
    def __init__(
        self,
        port: str,
        baud: int,
        on_frame: FrameCallback,
        on_event: EventCallback | None = None,
        writer: Any = None,
        reconnect_delay: float = 5.0,
    ) -> None:
        self._port = port
        self._baud = baud
        self._on_frame = on_frame
        self._on_event = on_event
        self._writer = writer
        self._reconnect_delay = reconnect_delay
        self._parser = FrameParser()
        self._stop_event = asyncio.Event()

        self._connected = False
        self._bytes_received: int = 0
        self._frames_parsed: int = 0
        self._events_parsed: int = 0
        self._errors: int = 0
        self._last_frame_ts: datetime | None = None
        self._connected_since: datetime | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "port": self._port,
            "baud": self._baud,
            "bytes_received": self._bytes_received,
            "frames_parsed": self._frames_parsed,
            "events_parsed": self._events_parsed,
            "errors": self._errors,
            "last_frame_ts": (
                self._last_frame_ts.isoformat() if self._last_frame_ts else None
            ),
            "connected_since": (
                self._connected_since.isoformat() if self._connected_since else None
            ),
        }

    async def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                reader, transport_writer = (
                    await serial_asyncio.open_serial_connection(
                        url=self._port, baudrate=self._baud
                    )
                )
                self._connected = True
                self._connected_since = datetime.now(tz=timezone.utc)
                log.info("serial.connected", port=self._port, baud=self._baud)

                if self._writer is not None:
                    self._writer.attach(transport_writer)

                try:
                    await self._pump(reader)
                finally:
                    self._connected = False
                    if self._writer is not None:
                        self._writer.detach()

            except Exception as exc:
                self._connected = False
                self._errors += 1
                log.warning(
                    "serial.disconnected",
                    exc=str(exc),
                    retry_in=self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)

    async def _pump(self, reader: asyncio.StreamReader) -> None:
        while not self._stop_event.is_set():
            chunk = await reader.read(256)
            if not chunk:
                break
            self._bytes_received += len(chunk)
            for byte in chunk:
                result = self._parser.feed(byte)
                if result is None:
                    continue
                if isinstance(result, FeatureFrame):
                    self._frames_parsed += 1
                    self._last_frame_ts = datetime.now(tz=timezone.utc)
                    try:
                        await self._on_frame(result)
                    except Exception:
                        self._errors += 1
                        log.exception("serial.frame_handler_error")
                elif isinstance(result, AeonEvent):
                    self._events_parsed += 1
                    log.info("serial.event", category=result.category,
                             name=result.name, arg=result.arg)
                    if self._on_event is not None:
                        try:
                            await self._on_event(result)
                        except Exception:
                            self._errors += 1
                            log.exception("serial.event_handler_error")

    def stop(self) -> None:
        self._stop_event.set()
