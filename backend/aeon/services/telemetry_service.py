# backend/aeon/services/telemetry_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict
from datetime import datetime, timezone

from shared.types import FeatureFrame

log = structlog.get_logger(__name__)


class TelemetryService:
    """
    Subsystem routing inbound telemetry packets, persisting them in EventMemory,
    and publishing update events.
    """

    def __init__(self, memory: Any, ws_bus: Any, event_bus: Any) -> None:
        self._memory = memory
        self._ws_bus = ws_bus
        self._event_bus = event_bus

    async def ingest_frame(self, frame: FeatureFrame) -> None:
        """Process an incoming feature frame/reading."""
        # Log to event memory
        await self._memory.log_event("SENSOR", "update", {
            "temperature": frame.temperature,
            "humidity": frame.humidity,
            "motion": frame.motion,
            "door_open": frame.door_open,
            "seq": frame.seq,
        })

        # Publish via EventBus and WebSocketBus
        await self._event_bus.publish("TelemetryReceived", {
            "seq": frame.seq,
            "temperature": frame.temperature,
            "motion": frame.motion,
        })

        if self._ws_bus:
            await self._ws_bus.publish("sensor_update", {
                "temperature": frame.temperature,
                "humidity": frame.humidity,
                "motion": frame.motion,
                "door_open": frame.door_open,
                "seq": frame.seq,
            })
