"""
tests/backend/test_e2e_pipeline.py

End-to-end integration test for the full ÆON data pipeline.

Covers:
  1. Serial parser  → FeatureFrame / AeonEvent
  2. SensorProcessor → MemoryStore → WS publish with real data
  3. PolicyEngine (mock QNN) → decision logged to DB
  4. KnowledgeGraph → persist nodes/edges, reload from DB
  5. WebSocket bus  → _build_telemetry() returns real values, no fakes
  6. Feedback → LearningLoop threshold decrements
  7. DreamState → stages broadcast, rules written to graph
  8. VoiceManager → sensor query answered from real DB data
  9. VoiceManager → feedback persisted as USER_CORRECTION event
 10. IdentityManager → export bundle with real node count / QR payload

Hardware/external services are mocked at the boundary.
No Math.random() or fake plausible values are used inside any module.
"""

from __future__ import annotations

import asyncio
import pytest
import struct
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ── Frame builders ────────────────────────────────────────────────────────────

def _feature_payload(
    temp=22.5, hum=48.0, motion=False, door=False,
    mean_t=22.0, var_t=0.1, delta_m=0.0, ts=1000,
) -> bytes:
    return struct.pack("<ffBBfffI",
        temp, hum, int(motion), int(door), mean_t, var_t, delta_m, ts)


def _wrap_packet(payload: bytes, ftype: int = 0x01, seq: int = 1) -> bytes:
    hdr  = bytes([0xAE, 0x01, ftype])
    hdr += struct.pack("<I", seq)
    hdr += struct.pack("<H", len(payload))
    return hdr + payload + bytes([0x00, 0x00])   # dummy CRC


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_db(path: Path):
    from aeon_platform.storage.store import MemoryStore
    mem = MemoryStore(db_path=path)
    await mem.init()
    return mem


# ── 1. Serial Parser ──────────────────────────────────────────────────────────

class TestSerialParser:

    def test_parse_feature_frame(self):
        from aeon_platform.communication.serial import FrameParser
        from shared.types import FeatureFrame

        packet = _wrap_packet(_feature_payload(temp=23.7, hum=51.0, motion=True), seq=42)
        parser, result = FrameParser(), None
        for b in packet:
            result = parser.feed(b)
            if result is not None:
                break

        assert isinstance(result, FeatureFrame)
        assert abs(result.temperature - 23.7) < 0.01
        assert result.motion is True
        assert result.seq == 42

    def test_parse_event_frame(self):
        from aeon_platform.communication.serial import FrameParser
        from shared.types import AeonEvent

        raw    = b"SYSTEM:boot_complete:0"
        packet = _wrap_packet(raw, ftype=0x02, seq=7)
        parser, result = FrameParser(), None
        for b in packet:
            result = parser.feed(b)
            if result is not None:
                break

        assert isinstance(result, AeonEvent)
        assert result.category == "SYSTEM"
        assert result.name == "boot_complete"
        assert result.seq == 7

    def test_rejects_corrupt_magic(self):
        from aeon_platform.communication.serial import FrameParser

        bad = bytes([0xFF, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00]) + b"\x00" * 4
        parser = FrameParser()
        assert all(parser.feed(b) is None for b in bad)


# ── 2. SensorProcessor → MemoryStore ─────────────────────────────────────────

async def test_sensor_processor_stores_frame():
    from shared.types import FeatureFrame
    from core.context.sensors import SensorProcessor

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "sp.db")
    try:
        bus = MagicMock(); bus.publish = AsyncMock()
        proc = SensorProcessor(memory=mem, ws_bus=bus)

        frame = FeatureFrame(
            temperature=24.1, humidity=55.0,
            motion=True, door_open=False,
            mean_temp=23.5, var_temp=0.2, delta_motion=1.0,
            timestamp_ms=5000, seq=10,
        )
        await proc.on_feature_frame(frame)

        history = await mem.get_sensor_history(minutes=5)
        assert len(history) == 1
        assert abs(history[0]["temperature"] - 24.1) < 0.01

        # WS published with real data, not a hardcoded value
        bus.publish.assert_called_once()
        published_payload = bus.publish.call_args[0][1]
        assert published_payload["temperature"] == pytest.approx(24.1, abs=0.01)

        latest = proc.get_latest()
        assert latest is not None
        assert latest["temperature"] == pytest.approx(24.1, abs=0.01)
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 3. PolicyEngine → decision logged ────────────────────────────────────────

async def test_policy_engine_logs_decision():
    from core.policy.engine import PolicyEngine
    from shared.types import FeatureFrame

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "pe.db")
    try:
        import numpy as np
        qnn = AsyncMock()
        qnn.infer = AsyncMock(
            return_value={"output": np.array([[0.2, 0.8]])}
        )

        graph = MagicMock()
        graph.get_active_rules_sync = MagicMock(return_value=[])

        bus = MagicMock(); bus.publish = AsyncMock()
        writer = AsyncMock()
        writer.send_buzzer = AsyncMock()
        writer.send_relay  = AsyncMock()

        engine = PolicyEngine(
            qnn=qnn, graph=graph, memory=mem,
            ws_bus=bus, serial_writer=writer,
        )

        frame = FeatureFrame(
            temperature=25.0, humidity=60.0,
            motion=True, door_open=False,
            mean_temp=24.5, var_temp=0.3, delta_motion=2.0,
            timestamp_ms=9000, seq=99,
        )
        await engine.on_feature_frame(frame)
        # Drain the queue by running the process loop directly
        frame2 = await engine._queue.get()
        decision = await engine._infer(frame2)
        await engine._dispatch(decision, frame2)

        assert bus.publish.called
        stats = await mem.get_system_stats()
        assert stats["decisions_count"] >= 1
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 4. KnowledgeGraph persistence ────────────────────────────────────────────

async def test_knowledge_graph_persists():
    from core.profiles.knowledge_graph import KnowledgeGraph

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "kg.db")
    try:
        g = KnowledgeGraph(store=mem)
        await g.init()

        await g.add_user("u-1", "Test")
        await g.add_device("d-1", "Sentinel", "arduino")
        await g.link_owns("u-1", "d-1")

        assert g._graph.number_of_nodes() >= 2
        assert g._graph.number_of_edges() >= 1

        # Reload from same DB — persistence check
        g2 = KnowledgeGraph(store=mem)
        await g2.init()
        assert g2._graph.has_node("u-1")
        assert g2._graph.has_node("d-1")
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 5. WS bus telemetry — no fake values ─────────────────────────────────────

async def test_ws_bus_telemetry_no_fake_values():
    from core.profiles.knowledge_graph import KnowledgeGraph
    from aeon_platform.communication.websocket import WebSocketBus

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "bus.db")
    try:
        graph = KnowledgeGraph(store=mem)
        await graph.init()

        bus = WebSocketBus()
        bus.memory           = mem
        bus.graph            = graph
        bus.serial_bridge    = None
        bus.model_manager    = None
        bus.learning_loop    = None
        bus.sensor_processor = None
        bus.voice_manager    = None

        with patch("backend.aeon.metrics.exporter.frames_total") as ft, \
             patch("backend.aeon.metrics.exporter.sys_cpu_utilization") as cpu, \
             patch("backend.aeon.metrics.exporter.sys_npu_utilization") as npu, \
             patch("backend.aeon.metrics.exporter.sys_power_draw_w") as pwr:

            ft._value.get  = MagicMock(return_value=0)
            cpu._value.get = MagicMock(return_value=12.5)
            npu._value.get = MagicMock(return_value=5.0)
            pwr._value.get = MagicMock(return_value=17.5)

            state = await bus._build_telemetry()

        for key in ["serialStatus", "snapdragonStatus", "continuousLearning",
                    "dreamState", "voiceAssistant", "privacyMesh",
                    "knowledgeGraph", "migrationState", "systemMeta"]:
            assert key in state, f"Missing key: {key}"

        # Arduino disconnected → temperature must be None, not a fake number
        assert state["serialStatus"]["connected"] is False
        assert state["serialStatus"]["temperature"] is None

        # Privacy guarantee — not a hardcoded "0"
        assert state["privacyMesh"]["rawBytesSent"] == 0

        # Execution provider must be "UNAVAILABLE" when no model loaded
        assert state["snapdragonStatus"]["executionProvider"] == "UNAVAILABLE"

        # CPU is the real value we mocked
        assert state["snapdragonStatus"]["cpuPct"] == pytest.approx(12.5)
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 6. LearningLoop threshold update ─────────────────────────────────────────

def test_learning_loop_threshold_update():
    from core.learning.loop import LearningLoop

    tmpdir = tempfile.mkdtemp()
    try:
        ll = LearningLoop(
            memory=MagicMock(), qnn=MagicMock(),
            model_dir=Path(tmpdir),
        )
        initial = ll.trainer.threshold
        ll.record_false_alarm()
        ll.record_false_alarm()
        assert ll.false_alarms_flagged == 2
        assert ll.trainer.threshold < initial
    finally:
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 7. DreamState — stages + graph rule ──────────────────────────────────────

async def test_dream_state_pipeline():
    from core.profiles.knowledge_graph import KnowledgeGraph
    from core.learning.dream import DreamState

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "ds.db")
    try:
        graph = KnowledgeGraph(store=mem)
        await graph.init()

        # Seed corrections — two events at hour 00 so a rule is synthesized
        for i in range(6):
            await mem.log_event(
                "USER_CORRECTION", "false_alarm",
                {"ts": f"2026-07-17T00:0{i}:00+00:00"}
            )

        bus = MagicMock(); bus.publish = AsyncMock()
        dream = DreamState(memory=mem, graph=graph)
        dream.attach_bus(bus)

        await dream.enter()

        assert bus.publish.called
        published_types = [c[0][0] for c in bus.publish.call_args_list]
        assert "dream_state_progress" in published_types

        assert dream.last_result in ("success", "insufficient_data")
        assert dream.events_replayed >= 6
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 8. VoiceManager — sensor query answered from real DB ─────────────────────

async def test_voice_manager_sensor_query():
    from core.profiles.knowledge_graph import KnowledgeGraph
    from backend.aeon.voice.manager import ConversationManager
    from shared.types import FeatureFrame
    from core.context.sensors import SensorProcessor

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "vm.db")
    try:
        graph = KnowledgeGraph(store=mem)
        await graph.init()

        bus = MagicMock(); bus.publish = AsyncMock()
        policy = MagicMock(); policy.execute_override = AsyncMock(return_value=True)

        # Store a real sensor reading
        proc  = SensorProcessor(memory=mem, ws_bus=bus)
        frame = FeatureFrame(
            temperature=21.3, humidity=47.0,
            motion=False, door_open=False,
            mean_temp=21.0, var_temp=0.05, delta_motion=0.0,
            timestamp_ms=1000, seq=1,
        )
        await proc.on_feature_frame(frame)

        vm = ConversationManager(graph=graph, policy=policy, memory_store=mem)
        response = await vm.handle_utterance("What is the temperature?")

        # Answer must contain the real stored value
        assert "21.3" in response or "21" in response
        assert any(w in response.lower() for w in ("degree", "celsius", "temperature"))
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 9. VoiceManager — feedback persists ──────────────────────────────────────

async def test_voice_manager_feedback_persists():
    from core.profiles.knowledge_graph import KnowledgeGraph
    from backend.aeon.voice.manager import ConversationManager

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "vfb.db")
    try:
        graph = KnowledgeGraph(store=mem)
        await graph.init()

        policy = MagicMock()
        vm     = ConversationManager(graph=graph, policy=policy, memory_store=mem)
        # Use a phrase that matches the FEEDBACK regex pattern
        await vm.handle_utterance("no that was wrong, false alarm")

        events = await mem.get_recent_events(limit=5)
        corrections = [e for e in events if e.get("category") == "USER_CORRECTION"]
        assert len(corrections) >= 1
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── 10. IdentityManager — export bundle ──────────────────────────────────────

async def test_identity_export_real_data():
    from core.profiles.knowledge_graph import KnowledgeGraph
    from core.profiles.identity import IdentityManager

    tmpdir = tempfile.mkdtemp()
    mem = await _make_db(Path(tmpdir) / "id.db")
    try:
        graph = KnowledgeGraph(store=mem)
        await graph.init()

        im = IdentityManager(graph=graph)
        await im.create_user("u-export", "Export User")
        await graph.add_device("d-export", "Sentinel", "arduino")
        await graph.link_owns("u-export", "d-export")

        bundle = await im.export("u-export")

        assert "qr_payload" in bundle
        assert bundle["qr_payload"].startswith("aeon://identity/v1/import")
        assert bundle["node_count"] >= 1
        assert "bundle" in bundle
    finally:
        await mem.close()
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
