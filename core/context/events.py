# core/context/events.py

from __future__ import annotations

import structlog
from typing import Any

log = structlog.get_logger(__name__)


class EventProcessor:
    def __init__(self, memory: Any, ws_bus: Any) -> None:
        self._memory = memory
        self._ws_bus = ws_bus

    async def on_event(self, event: Any) -> None:
        """Process incoming system event."""
        # Classify and enrich
        payload = {
            "category": event.category,
            "name": event.name,
            "arg": event.arg,
            "seq": event.seq,
        }
        
        # Store in persistent log
        await self._memory.log_event(event.category, event.name, payload)
        
        # Publish to real-time bus
        await self._ws_bus.publish("system_event", payload)

    async def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Fetch recent events for dashboard timeline."""
        return await self._memory.get_recent_events(limit)
