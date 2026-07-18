# core/registry/devices.py

from __future__ import annotations

import structlog
from typing import Any, Dict, List
from datetime import datetime, timezone

log = structlog.get_logger(__name__)


class DeviceRegistry:
    def __init__(self, graph: Any, ws_bus: Any) -> None:
        self._graph = graph
        self._ws_bus = ws_bus

    async def register_device(self, device_id: str, device_type: str, metadata: dict = None) -> None:
        """Register a device and announce it on the bus with full capability model."""
        meta = metadata or {}
        now = datetime.now(tz=timezone.utc).isoformat()

        # Map capabilities based on type
        capabilities = ["sensors"]
        if device_type in ("sentinel", "arduino"):
            capabilities.extend(["climate", "notifications", "switches"])
        elif device_type == "gateway":
            capabilities.extend(["lighting", "switches"])

        default_metrics = {
            "capabilities": capabilities,
            "health": "healthy",
            "battery_status": 100,  # percentage
            "firmware_version": "2.0.0",
            "communication_quality": 1.0,  # 0.0 - 1.0
            "reliability": 1.0,            # 0.0 - 1.0
            "average_response_time_ms": 15.0,
            "error_count": 0,
            "success_count": 1,
            "device_confidence": 1.0,
            "associated_contexts": ["home", "office"],
            "associated_activities": ["Working", "Sleeping"],
            "last_successful_command": now,
        }

        # Override defaults with provided metadata
        default_metrics.update(meta)

        await self._graph.upsert_node(
            device_id, 
            type="device", 
            device_type=device_type,
            status="online",
            last_seen=now,
            **default_metrics
        )
        log.info("device.registered", device_id=device_id, type=device_type)
        if self._ws_bus:
            await self._ws_bus.publish("device_status", {"id": device_id, "status": "online"})

    async def heartbeat(self, device_id: str) -> None:
        """Update last seen timestamp for a device."""
        if device_id in self._graph._graph:
            now = datetime.now(tz=timezone.utc).isoformat()
            await self._graph.upsert_node(device_id, last_seen=now, status="online")

    async def update_device_metrics(self, device_id: str, latency_ms: float, success: bool) -> None:
        """Update runtime health and latency stats for the device."""
        if device_id not in self._graph._graph:
            return

        node = self._graph._graph.nodes[device_id]
        success_count = int(node.get("success_count", 0))
        error_count = int(node.get("error_count", 0))
        avg_latency = float(node.get("average_response_time_ms", 15.0))

        if success:
            success_count += 1
        else:
            error_count += 1

        total = max(1, success_count + error_count)
        reliability = round(success_count / total, 3)
        
        # EMA for latency
        avg_latency = round(0.1 * latency_ms + 0.9 * avg_latency, 1)

        # Health estimation based on reliability
        health = "healthy"
        if reliability < 0.70:
            health = "critical"
        elif reliability < 0.90:
            health = "warning"

        updates = {
            "success_count": success_count,
            "error_count": error_count,
            "reliability": reliability,
            "average_response_time_ms": avg_latency,
            "health": health,
            "device_confidence": reliability,
        }
        if success:
            updates["last_successful_command"] = datetime.now(timezone.utc).isoformat()

        await self._graph.upsert_node(device_id, **updates)
        log.debug("device.metrics_updated", device_id=device_id, reliability=reliability, latency=avg_latency)

    async def check_capability(self, device_id: str, capability: str) -> bool:
        """Return True if device supports specific capability."""
        if device_id not in self._graph._graph:
            return False
        node = self._graph._graph.nodes[device_id]
        caps = node.get("capabilities", [])
        return capability.lower() in [c.lower() for c in caps]

    async def get_all_devices(self) -> list[dict[str, Any]]:
        """List all registered devices."""
        devices = []
        for n, d in self._graph._graph.nodes(data=True):
            if d.get("type") == "device":
                dev = {"id": n}
                dev.update({k: v for k, v in d.items() if k != "type"})
                devices.append(dev)
        return devices
