# backend/aeon/services/firmware_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict, List

log = structlog.get_logger(__name__)


class FirmwareService:
    """Tracks active firmware versions, compatibility checks, and update logs."""

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    async def log_firmware_version(self, device_id: str, version: str) -> None:
        """Register the device's current running firmware version in the Graph."""
        await self._graph.upsert_node(
            device_id,
            firmware_version=version,
        )
        log.info("firmware.version_logged", device=device_id, version=version)

    async def check_compatibility(self, device_id: str, required_ver: str) -> bool:
        """Check if the device's firmware satisfies compatibility constraints."""
        if device_id not in self._graph._graph:
            return False
        node = self._graph._graph.nodes[device_id]
        installed = node.get("firmware_version", "1.0.0")
        
        # Simple semver verification: compare major versions
        try:
            inst_major = int(installed.split(".")[0])
            req_major = int(required_ver.split(".")[0])
            return inst_major >= req_major
        except (ValueError, IndexError):
            return False
