"""
aeon/serial/bridge.py — Async USB-serial bridge.

Reads the AEON binary protocol from the Arduino Sentinel and dispatches
decoded FeatureFrame objects to the registered callback.

Frame format (matches arduino/libraries/aeon_protocol/aeon_protocol.h):
  [0xAE][0x01][TYPE:1][SEQ:4LE][LEN:2LE][PAYLOAD:LEN][CRC16:2LE]
"""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timezone
from typing import Callable, Awaitable, Any

import serial_asyncio  # pip install pyserial-asyncio

from aeon.serial.parser import FrameParser, FeatureFrame, AeonEvent

log = structlog.get_logger(__name__)

FrameCallback = Callable[[FeatureFrame], Awaitable[None]]
EventCallback = Callable[[AeonEvent], Awaitable[None]]


class SerialBridge:
    """
    Async wrapper around a serial port.

    Usage::

        bridge = SerialBridge(port="/dev/ttyUSB0", baud=115200,
                              on_frame=handler, on_event=evt_handler,
                              writer=serial_writer)
        await bridge.run()   # runs forever; call bridge.stop() to shut down
    """

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
        self._writer = writer           # SerialWriter instance
        self._reconnect_delay = reconnect_delay
        self._parser = FrameParser()
        self._stop_event = asyncio.Event()

        # Status tracking
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
        """Return connection and throughput status for dashboard."""
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
        """Connect and pump bytes until stop() is called."""
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

                # Attach the writer transport so commands can be sent to Arduino
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
