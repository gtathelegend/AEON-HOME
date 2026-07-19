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
    Sends COMMAND JSON payloads to the Arduino over USB Serial or WebSocket transport.
    """

    def __init__(self) -> None:
        self._sockets: list[WebSocket] = []
        self._serial_transport_writer: Any = None
        self._seq: int = 0
        self._lock = asyncio.Lock()
        self._commands_sent: int = 0

    def attach(self, websocket: WebSocket) -> None:
        if websocket not in self._sockets:
            self._sockets.append(websocket)
        log.info("serial_writer.attached_ws", clients=len(self._sockets))

    def detach(self, websocket: WebSocket) -> None:
        if websocket in self._sockets:
            self._sockets.remove(websocket)
        log.info("serial_writer.detached_ws", clients=len(self._sockets))

    def attach_serial(self, writer: Any) -> None:
        self._serial_transport_writer = writer
        log.info("serial_writer.attached_serial")

    def detach_serial(self) -> None:
        self._serial_transport_writer = None
        log.info("serial_writer.detached_serial")

    @property
    def is_connected(self) -> bool:
        return self._serial_transport_writer is not None or len(self._sockets) > 0

    @property
    def commands_sent(self) -> int:
        return self._commands_sent

    async def send_json(self, payload: dict) -> bool:
        if not self.is_connected:
            log.warning("serial_writer.not_connected — command dropped", typ=payload.get("typ"))
            return False

        async with self._lock:
            self._seq += 1
            payload["seq"] = self._seq
            
            import json
            json_str = json.dumps(payload) + "\n"
            sent_count = 0

            # 1. Send via direct USB Serial port
            if self._serial_transport_writer is not None:
                try:
                    self._serial_transport_writer.write(json_str.encode("utf-8"))
                    await self._serial_transport_writer.drain()
                    sent_count += 1
                    log.info("Command Sent via Serial", typ=payload.get("typ"), seq=self._seq)
                except Exception:
                    log.exception("serial_writer.serial_send_error")

            # 2. Send via connected WebSocket clients (if any)
            for ws in list(self._sockets):
                try:
                    await ws.send_text(json_str)
                    sent_count += 1
                except Exception:
                    log.exception("serial_writer.ws_send_error")

            if sent_count > 0:
                self._commands_sent += 1
                return True
            return False

    async def send_relay(self, relay_id: int, state: bool) -> bool:
        return await self.send_json({
            "typ": "relay_set",
            "relay": relay_id,
            "state": state,
        })

    async def send_fan_speed(self, speed: int) -> bool:
        return await self.send_json({
            "typ": "fan_set",
            "speed": speed,
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
    """
    Dedicated SerialManager / SerialBridge continuously reading from USB Serial (COM10).
    Auto-connects on startup and auto-reconnects on disconnect.
    """

    def __init__(
        self,
        port: str,
        baud: int,
        on_frame: FrameCallback,
        on_event: EventCallback | None = None,
        writer: Any = None,
        gateway: Any = None,
        reconnect_delay: float = 3.0,
    ) -> None:
        self._port = port
        self._baud = baud
        self._on_frame = on_frame
        self._on_event = on_event
        self._writer = writer
        self._gateway = gateway
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
                log.info("Serial Connected", port=self._port, baud=self._baud)

                if self._writer is not None:
                    if hasattr(self._writer, "attach_serial"):
                        self._writer.attach_serial(transport_writer)
                    else:
                        self._writer.attach(transport_writer)

                try:
                    await self._pump(reader)
                finally:
                    self._connected = False
                    if self._writer is not None:
                        if hasattr(self._writer, "detach_serial"):
                            self._writer.detach_serial()
                        else:
                            self._writer.detach()

            except Exception as exc:
                self._connected = False
                self._errors += 1
                log.warning(
                    "Serial Disconnected",
                    error=str(exc),
                    retry_in=self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)

    async def _pump(self, reader: asyncio.StreamReader) -> None:
        while not self._stop_event.is_set():
            chunk = await reader.readline()
            if not chunk:
                break
            self._bytes_received += len(chunk)
            log.info("Packet Received", bytes_len=len(chunk))
            
            # 1. Parse as binary stream
            for byte in chunk:
                result = self._parser.feed(byte)
                if result is not None:
                    if isinstance(result, FeatureFrame):
                        self._frames_parsed += 1
                        self._last_frame_ts = datetime.now(tz=timezone.utc)
                        log.info("Packet Parsed", typ="binary_feature_frame", seq=result.seq)
                        try:
                            await self._on_frame(result)
                            log.info("Broadcast Sent", type="sensor_update")
                        except Exception:
                            self._errors += 1
                            log.exception("serial.frame_handler_error")
                    elif isinstance(result, AeonEvent):
                        self._events_parsed += 1
                        log.info("Packet Parsed", typ="binary_event", category=result.category, seq=result.seq)
                        if self._on_event is not None:
                            try:
                                await self._on_event(result)
                                log.info("Broadcast Sent", type="event_update")
                            except Exception:
                                self._errors += 1
                                log.exception("serial.event_handler_error")

            # 2. Parse as text JSON lines
            try:
                line_str = chunk.decode("utf-8", errors="ignore").strip()
                json_part = ""
                if "Payload:" in line_str:
                    json_part = line_str.split("Payload:", 1)[1].strip()
                elif "{" in line_str:
                    json_part = line_str[line_str.index("{"):]

                if json_part and json_part.startswith("{") and json_part.endswith("}"):
                    import json
                    data = json.loads(json_part)
                    typ = data.get("typ")
                    seq = int(data.get("seq", data.get("sequence", 0)))
                    log.info("Packet Parsed", typ=typ or "json_telemetry", seq=seq)

                    # Route through CommunicationGateway if available
                    if self._gateway is not None:
                        try:
                            await self._gateway.handle_incoming(json_part, websocket=None)
                        except Exception:
                            log.exception("serial.gateway_routing_error")

                    if typ == "sensor_update":
                        frame = FeatureFrame.from_json(data)
                        self._frames_parsed += 1
                        self._last_frame_ts = datetime.now(tz=timezone.utc)
                        try:
                            await self._on_frame(frame)
                            log.info("Broadcast Sent", type="sensor_update")
                        except Exception:
                            self._errors += 1
                            log.exception("serial.json_frame_handler_error")
                    elif typ == "heartbeat":
                        event = AeonEvent(
                            category="system",
                            name="heartbeat",
                            arg=seq,
                            seq=seq
                        )
                        self._events_parsed += 1
                        if self._on_event is not None:
                            try:
                                await self._on_event(event)
                                log.info("Broadcast Sent", type="heartbeat")
                            except Exception:
                                self._errors += 1
                                log.exception("serial.json_event_handler_error")
            except Exception as e:
                log.debug("serial.parse_line_ignored", raw=chunk, error=str(e))

    def stop(self) -> None:
        self._stop_event.set()


# Dedicated SerialManager alias for SerialBridge
SerialManager = SerialBridge

