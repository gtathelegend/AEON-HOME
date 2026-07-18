# backend/aeon/services/device_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict, List
from datetime import datetime, timezone

log = structlog.get_logger(__name__)


class DeviceService:
    """
    Application Service layer managing device capabilities, connectivity heartbeats,
    and runtime reliability reports. Mirrored directly in the Knowledge Graph.
    """

    def __init__(self, device_registry: Any, event_bus: Any) -> None:
        self._registry = device_registry
        self._event_bus = event_bus

    async def register(self, device_id: str, device_type: str, metadata: dict = None) -> None:
        await self._registry.register_device(device_id, device_type, metadata)
        await self._event_bus.publish("DeviceConnected", {"device_id": device_id, "type": device_type})

    async def ping(self, device_id: str) -> None:
        await self._registry.heartbeat(device_id)

    async def update_reliability(self, device_id: str, latency_ms: float, success: bool) -> None:
        await self._registry.update_device_metrics(device_id, latency_ms, success)

    async def get_inventory(self) -> List[Dict[str, Any]]:
        return await self._registry.get_all_devices()

    async def check_device_capability(self, device_id: str, capability: str) -> bool:
        return await self._registry.check_capability(device_id, capability)
