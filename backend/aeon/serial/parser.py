"""
aeon/serial/parser.py — AEON binary protocol state-machine parser (Python side).

Mirrors the Arduino receive state machine in aeon_protocol.cpp.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Union


class FrameType(IntEnum):
    FEATURE_FRAME = 0x01
    EVENT         = 0x02
    COMMAND       = 0x10
    ACK           = 0xFF


@dataclass
class FeatureFrame:
    temperature:   float
    humidity:      float
    motion:        bool
    door_open:     bool
    mean_temp:     float
    var_temp:      float
    delta_motion:  float
    timestamp_ms:  int
    seq:           int

    # Struct layout must match Arduino FeatureFrame exactly (little-endian)
    _STRUCT = struct.Struct("<ffBBfffI")

    @classmethod
    def from_bytes(cls, data: bytes, seq: int) -> "FeatureFrame":
        t, h, m, d, mt, vt, dm, ts = cls._STRUCT.unpack_from(data)
        return cls(
            temperature=t, humidity=h,
            motion=bool(m), door_open=bool(d),
            mean_temp=mt, var_temp=vt,
            delta_motion=dm, timestamp_ms=ts,
            seq=seq,
        )

    @classmethod
    def from_json(cls, data: dict) -> "FeatureFrame":
        return cls(
            temperature=float(data.get("temp", 0.0)),
            humidity=float(data.get("humidity", 0.0)),
            motion=bool(data.get("motion", False)),
            door_open=bool(data.get("door", False)),
            mean_temp=float(data.get("mean_t", 0.0)),
            var_temp=float(data.get("var_t", 0.0)),
            delta_motion=float(data.get("d_motion", 0.0)),
            timestamp_ms=int(data.get("ts", 0)),
            seq=int(data.get("seq", 0)),
        )


@dataclass
class AeonEvent:
    category: str
    name:     str
    arg:      int
    seq:      int

    @classmethod
    def from_json(cls, data: dict) -> "AeonEvent":
        # Handle feedback_event etc
        # Usually data looks like {"typ": "feedback_event", "device_id": "...", "event": "false_alarm"}
        # Or {"typ": "memory_status", "pct": 45}
        typ = data.get("typ", "unknown")
        
        category = "feedback"
        name = "unknown"
        arg = 0

        if typ == "feedback_event":
            category = "feedback"
            name = data.get("event", "unknown")
            arg = data.get("arg", 1)
        elif typ == "memory_status":
            category = "memory"
            name = "usage"
            arg = data.get("pct", 0)
        elif typ == "model_ack":
            category = "model"
            name = "ack"
            arg = data.get("model_v", 0)
        elif typ == "policy_ack":
            category = "policy"
            name = "ack"
            arg = 0

        return cls(
            category=category,
            name=name,
            arg=int(arg),
            seq=int(data.get("seq", 0)),
        )


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

    MAGIC = (0xAE, 0x01)

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
