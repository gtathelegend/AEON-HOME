"""
aeon/main.py — ÆON Backend entry point.

Starts all subsystems concurrently:
  1. Serial bridge   (Arduino → feature frames)
  2. QNN inference   (feature frames → AI decisions)
  3. Policy engine   (AI decisions → actuation commands)
  4. Knowledge graph (preference + context updates)
  5. WebSocket bus   (push events to PWA dashboard)
  6. FastAPI server  (REST API for dashboard + mobile)
  7. Metrics server  (Prometheus /metrics endpoint)
"""

import asyncio
import structlog

from aeon_platform.filesystem.settings import settings
from aeon_platform.runtime.qnn.manager import QNNManager
from core.policy.engine import PolicyEngine
from core.profiles.knowledge_graph import KnowledgeGraph
from aeon_platform.communication.websocket import WebSocketBus
from aeon_platform.storage.store import MemoryStore
from backend.aeon.api.app import create_app
from backend.aeon.metrics.exporter import MetricsExporter
from aeon_platform.communication.serial import SerialWriter
from core.context.sensors import SensorProcessor
from core.context.events import EventProcessor
from backend.aeon.models.manager import ModelManager
from core.profiles.identity import IdentityManager
from core.registry.devices import DeviceRegistry
from core.learning.loop import LearningLoop

log = structlog.get_logger(__name__)


async def main() -> None:
    log.info("aeon.start", version="1.0.0", device=settings.device_id)

    # ── Shared infrastructure ─────────────────────────────────────────────────
    memory   = MemoryStore(db_path=settings.memory_db_path)
    await memory.init()

    graph    = KnowledgeGraph(store=memory)
    await graph.init()

    # Seed database if requested
    if settings.seed_database:
        from aeon_platform.storage.seed import seed_database_if_empty
        await seed_database_if_empty(memory, graph)

    ws_bus   = WebSocketBus()
    metrics  = MetricsExporter()

    qnn      = QNNManager(
        model_dir=settings.model_dir,
        use_npu=settings.use_npu,
    )
    await qnn.init()

    # ── New Modules ───────────────────────────────────────────────────────────
    serial_writer    = SerialWriter()
    sensor_processor = SensorProcessor(memory=memory, ws_bus=ws_bus)
    event_processor  = EventProcessor(memory=memory, ws_bus=ws_bus)
    model_manager    = ModelManager(qnn=qnn, model_dir=settings.model_dir)
    identity_manager = IdentityManager(graph=graph)
    device_registry  = DeviceRegistry(graph=graph, ws_bus=ws_bus)
    learning_loop    = LearningLoop(memory=memory, qnn=qnn, model_dir=settings.model_dir)

    policy   = PolicyEngine(
        qnn=qnn,
        graph=graph,
        memory=memory,
        ws_bus=ws_bus,
        serial_writer=serial_writer,
        device_registry=device_registry,
    )

    from backend.aeon.voice.manager import ConversationManager
    voice_manager = ConversationManager(graph=graph, policy=policy, memory_store=memory)

    # ── Wire cross-module dependencies ────────────────────────────────────────
    # WebSocket bus gets references to every real data source
    ws_bus.memory           = memory
    ws_bus.model_manager    = model_manager
    ws_bus.learning_loop    = learning_loop
    ws_bus.policy           = policy
    ws_bus.device_registry  = device_registry
    ws_bus.serial_bridge    = serial_writer
    ws_bus.voice_manager    = voice_manager
    ws_bus.sensor_processor = sensor_processor
    ws_bus.graph            = graph        # for real node/edge counts
    ws_bus.identity_manager = identity_manager

    # Learning loop gets bus so DreamState can broadcast progress stages
    learning_loop.attach_bus(ws_bus)
    # Give DreamState the real knowledge graph
    learning_loop.attach_graph(graph)

    # Voice manager gets bus so it can publish voice_status events
    voice_manager.attach_bus(ws_bus)

    # WebSocket bus needs a reference to a bridge-like object for telemetry status
    class DummyBridge:
        def __init__(self, writer):
            self._frames_parsed = 0
            self._writer = writer
        def get_status(self):
            return {
                "connected": self._writer.is_connected,
                "port": "Wi-Fi (Gateway)",
                "baud": 115200,
                "frames_parsed": self._frames_parsed,
                "last_frame_ts": None
            }
    ws_bus.serial_bridge = DummyBridge(serial_writer)

    app      = create_app(
        memory=memory,
        graph=graph,
        ws_bus=ws_bus,
        policy=policy,
        metrics=metrics,
        sensor_processor=sensor_processor,
        event_processor=event_processor,
        model_manager=model_manager,
        learning_loop=learning_loop,
        serial_bridge=ws_bus.serial_bridge,
        serial_writer=serial_writer,
        identity_manager=identity_manager,
        device_registry=device_registry,
        voice_manager=voice_manager,
    )

    # ── Run all subsystems ────────────────────────────────────────────────────
    async with asyncio.TaskGroup() as tg:
        tg.create_task(policy.run(),         name="policy-engine")
        tg.create_task(ws_bus.run(),         name="ws-bus")
        tg.create_task(metrics.run(),        name="metrics-exporter")
        tg.create_task(learning_loop.run(),  name="learning-loop")
        tg.create_task(
            __import__("uvicorn").Server(
                __import__("uvicorn").Config(
                    app,
                    host=settings.api_host,
                    port=settings.api_port,
                    log_level="warning",
                )
            ).serve(),
            name="api-server",
        )


if __name__ == "__main__":
    asyncio.run(main())
