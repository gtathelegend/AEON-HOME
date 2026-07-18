"""
aeon/devices/registry.py — Connected device registry.

Tracks state and metadata for all connected devices (Arduino nodes, mobile clients).
"""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

if TYPE_CHECKING:
    from aeon.graph.knowledge_graph import KnowledgeGraph
    from aeon.websocket.bus import WebSocketBus

log = structlog.get_logger(__name__)


class DeviceRegistry:
    def __init__(self, graph: "KnowledgeGraph", ws_bus: "WebSocketBus") -> None:
        self._graph = graph
        self._ws_bus = ws_bus

    async def register_device(self, device_id: str, device_type: str, metadata: dict = None) -> None:
        """Register a device and announce it on the bus."""
        meta = metadata or {}
        now = datetime.now(tz=timezone.utc).isoformat()
        await self._graph.upsert_node(
            device_id, 
            type="device", 
            device_type=device_type,
            status="online",
            last_seen=now,
            **meta
        )
        log.info("device.registered", device_id=device_id, type=device_type)
        await self._ws_bus.publish("device_status", {"id": device_id, "status": "online"})

    async def heartbeat(self, device_id: str) -> None:
        """Update last seen timestamp for a device."""
        if device_id in self._graph._graph:
            now = datetime.now(tz=timezone.utc).isoformat()
            await self._graph.upsert_node(device_id, last_seen=now, status="online")
            
    async def get_all_devices(self) -> list[dict[str, Any]]:
        """List all registered devices."""
        devices = []
        for n, d in self._graph._graph.nodes(data=True):
            if d.get("type") == "device":
                dev = {"id": n}
                dev.update({k: v for k, v in d.items() if k != "type"})
                devices.append(dev)
        return devices
