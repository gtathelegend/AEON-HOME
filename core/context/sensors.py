# core/context/sensors.py

from __future__ import annotations

import structlog
from typing import Any

log = structlog.get_logger(__name__)


class SensorProcessor:
    def __init__(self, memory: Any, ws_bus: Any) -> None:
        self._memory = memory
        self._ws_bus = ws_bus
        self._latest_frame: Any = None

    async def on_feature_frame(self, frame: Any) -> None:
        """Process incoming feature frame."""
        # 1. Validation
        if not (-40.0 <= frame.temperature <= 85.0):
            log.warning("sensor.invalid_temperature", temp=frame.temperature)
            # Clamp or drop, choosing clamp for demo stability
            frame.temperature = max(-40.0, min(85.0, frame.temperature))
            
        if not (0.0 <= frame.humidity <= 100.0):
            log.warning("sensor.invalid_humidity", hum=frame.humidity)
            frame.humidity = max(0.0, min(100.0, frame.humidity))

        self._latest_frame = frame

        # 2. Store to persistent memory
        await self._memory.log_feature(frame)

        # 3. Publish to real-time bus
        await self._ws_bus.publish("sensor_update", {
            "seq": frame.seq,
            "timestamp_ms": frame.timestamp_ms,
            "temperature": frame.temperature,
            "humidity": frame.humidity,
            "motion": frame.motion,
            "door_open": frame.door_open,
            "mean_temp": frame.mean_temp,
            "var_temp": frame.var_temp,
            "delta_motion": frame.delta_motion
        })

    def get_latest(self) -> dict[str, Any] | None:
        """Return the most recent validated feature frame data."""
        if not self._latest_frame:
            return None
        return {
            "seq": self._latest_frame.seq,
            "timestamp_ms": self._latest_frame.timestamp_ms,
            "temperature": self._latest_frame.temperature,
            "humidity": self._latest_frame.humidity,
            "motion": self._latest_frame.motion,
            "door_open": self._latest_frame.door_open,
            "mean_temp": self._latest_frame.mean_temp,
            "var_temp": self._latest_frame.var_temp,
            "delta_motion": self._latest_frame.delta_motion
        }

    async def get_history(self, minutes: int = 60) -> list[dict]:
        """Fetch historical sensor data for charting."""
        return await self._memory.get_sensor_history(minutes)
