"""
tests/backend/test_serial_parser.py

Unit tests for the AEON serial protocol parser.
These run without hardware — we synthesise frames manually.
"""

import struct
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from aeon_platform.communication.serial import FrameParser, FrameType
from shared.types import FeatureFrame, AeonEvent


# ── Helpers ────────────────────────────────────────────────────────────────────

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    return crc


def build_frame(frame_type: int, seq: int, payload: bytes) -> bytes:
    header = struct.pack("<BBB", 0xAE, 0x01, frame_type)
    header += struct.pack("<I", seq)
    header += struct.pack("<H", len(payload))
    body = bytes([frame_type]) + struct.pack("<I", seq) + struct.pack("<H", len(payload)) + payload
    crc = crc16(body)
    return header + payload + struct.pack("<H", crc)


def make_feature_frame_payload(
    temp=21.5, hum=48.0, motion=False, door=False,
    mean_t=21.0, var_t=0.1, delta_m=0.0, ts=12345
) -> bytes:
    return struct.pack(
        "<ffBBfffI",
        temp, hum, int(motion), int(door), mean_t, var_t, delta_m, ts
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

def feed_frame(parser: FrameParser, raw: bytes):
    results = []
    for b in raw:
        r = parser.feed(b)
        if r is not None:
            results.append(r)
    return results


def test_valid_feature_frame_parsed():
    payload = make_feature_frame_payload(temp=22.3, motion=True)
    raw = build_frame(FrameType.FEATURE_FRAME, seq=1, payload=payload)
    parser = FrameParser()
    results = feed_frame(parser, raw)
    assert len(results) == 1
    frame = results[0]
    assert isinstance(frame, FeatureFrame)
    assert abs(frame.temperature - 22.3) < 0.01
    assert frame.motion is True
    assert frame.seq == 1


def test_event_frame_parsed():
    payload = b"boot:state_restored:42"
    raw = build_frame(FrameType.EVENT, seq=0, payload=payload)
    parser = FrameParser()
    results = feed_frame(parser, raw)
    assert len(results) == 1
    event = results[0]
    assert isinstance(event, AeonEvent)
    assert event.category == "boot"
    assert event.name == "state_restored"
    assert event.arg == 42


def test_garbage_before_frame_ignored():
    payload = make_feature_frame_payload()
    raw = b"\x00\xFF\x12\x34" + build_frame(FrameType.FEATURE_FRAME, seq=5, payload=payload)
    parser = FrameParser()
    results = feed_frame(parser, raw)
    assert len(results) == 1
    assert isinstance(results[0], FeatureFrame)
    assert results[0].seq == 5


def test_two_consecutive_frames():
    p1 = make_feature_frame_payload(temp=20.0)
    p2 = make_feature_frame_payload(temp=21.0)
    raw = (build_frame(FrameType.FEATURE_FRAME, seq=1, payload=p1) +
           build_frame(FrameType.FEATURE_FRAME, seq=2, payload=p2))
    parser = FrameParser()
    results = feed_frame(parser, raw)
    assert len(results) == 2
    assert results[0].seq == 1
    assert results[1].seq == 2


def test_truncated_frame_no_result():
    payload = make_feature_frame_payload()
    raw = build_frame(FrameType.FEATURE_FRAME, seq=1, payload=payload)
    parser = FrameParser()
    # Feed only half
    results = feed_frame(parser, raw[:len(raw) // 2])
    assert results == []


@pytest.mark.asyncio
async def test_serial_manager_json_parsing():
    from aeon_platform.communication.serial import SerialManager
    import asyncio

    parsed_frames = []
    parsed_events = []

    async def on_frame(f):
        parsed_frames.append(f)

    async def on_event(e):
        parsed_events.append(e)

    manager = SerialManager("COM10", 115200, on_frame=on_frame, on_event=on_event)

    class DummyReader:
        def __init__(self, lines):
            self.lines = lines
            self.idx = 0
        async def readline(self):
            if self.idx < len(self.lines):
                res = self.lines[self.idx]
                self.idx += 1
                return res
            return b""

    sample_json = b'{"protocol_version":1,"typ":"sensor_update","temp":24.5,"humidity":52.0,"motion":1,"sequence":12}\n'
    reader = DummyReader([sample_json])
    await manager._pump(reader)

    assert len(parsed_frames) == 1
    assert parsed_frames[0].temperature == 24.5
    assert parsed_frames[0].humidity == 52.0
    assert parsed_frames[0].motion is True
    assert parsed_frames[0].seq == 12


@pytest.mark.asyncio
async def test_serial_writer_attach_serial():
    from aeon_platform.communication.serial import SerialWriter

    writer = SerialWriter()
    written_chunks = []

    class DummyTransportWriter:
        def write(self, data):
            written_chunks.append(data)
        async def drain(self):
            pass

        def get_extra_info(self, name):
            return None

    transport_writer = DummyTransportWriter()
    writer.attach_serial(transport_writer)
    assert writer.is_connected is True

    ok = await writer.send_fan_speed(75)
    assert ok is True
    assert len(written_chunks) == 1
    assert b'"typ": "fan_set"' in written_chunks[0]
    assert b'"speed": 75' in written_chunks[0]

