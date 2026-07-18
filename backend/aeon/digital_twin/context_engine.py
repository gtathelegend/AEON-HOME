"""
aeon/digital_twin/context_engine.py

ContextEngine — aggregates live sensor telemetry and policy decisions
into a unified room-context state that drives Digital Twin appliance models.

Context state includes:
  temperature       — latest °C reading from DHT22
  humidity          — latest %RH reading
  motion_active     — True if PIR detected motion in last N seconds
  occupancy_score   — rolling 0–1 estimate of room occupancy
  time_of_day       — "morning" | "afternoon" | "evening" | "night"
  ambient_lux       — estimated lux (derived from time_of_day; extend with LDR)
  recent_events     — last 10 event names from memory store
"""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timezone
from typing import Any

log = structlog.get_logger(__name__)

MOTION_WINDOW_SECONDS = 30   # motion considered "active" for this window
OCCUPANCY_ALPHA       = 0.15 # EMA smoothing factor for occupancy score


def _time_of_day() -> str:
    h = datetime.now(timezone.utc).hour
    if  6 <= h < 12: return "morning"
    if 12 <= h < 18: return "afternoon"
    if 18 <= h < 22: return "evening"
    return "night"


def _estimated_lux(time_of_day: str) -> float:
    return {"morning": 800, "afternoon": 1500, "evening": 200, "night": 5}[time_of_day]


class ContextEngine:
    """
    Aggregates sensor telemetry into a room-context dict consumed by
    SmartACTwin, SmartLightTwin, and RobotVacuumTwin.

    Usage:
        ctx = ContextEngine(memory_store)
        await ctx.refresh()
        state = ctx.state
    """

    def __init__(self, memory_store: Any) -> None:
        self._store = memory_store
        self._occupancy: float = 0.0
        self._last_motion_ts: float = 0.0

        self.state: dict[str, Any] = {
            "temperature":    None,
            "humidity":       None,
            "motion_active":  False,
            "occupancy_score": 0.0,
            "time_of_day":    _time_of_day(),
            "ambient_lux":    _estimated_lux(_time_of_day()),
            "recent_events":  [],
        }

    async def refresh(self) -> dict[str, Any]:
        """Pull latest data from the memory store and update context state."""
        import time
        now = time.time()

        try:
            # Latest sensor frame
            row = await self._store.get_latest_sensor()
            if row:
                self.state["temperature"] = row.get("temperature")
                self.state["humidity"]    = row.get("humidity")

                motion_now = bool(row.get("motion"))
                if motion_now:
                    self._last_motion_ts = now

                active = (now - self._last_motion_ts) < MOTION_WINDOW_SECONDS
                self.state["motion_active"] = active

                # EMA occupancy
                signal = 1.0 if active else 0.0
                self._occupancy = OCCUPANCY_ALPHA * signal + (1 - OCCUPANCY_ALPHA) * self._occupancy
                self.state["occupancy_score"] = round(self._occupancy, 3)

            # Recent events (for context awareness)
            events = await self._store.get_recent_events(limit=10)
            self.state["recent_events"] = [e.get("name", "") for e in events]

        except Exception:
            log.exception("context_engine.refresh_error")

        tod = _time_of_day()
        self.state["time_of_day"]   = tod
        self.state["ambient_lux"]   = _estimated_lux(tod)

        log.debug("context_engine.refreshed", state=self.state)
        return self.state

    async def run_loop(self, interval_s: float = 5.0) -> None:
        """Background task: refresh context every interval_s seconds."""
        while True:
            await self.refresh()
            await asyncio.sleep(interval_s)
