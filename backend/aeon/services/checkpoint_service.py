# backend/aeon/services/checkpoint_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict
from datetime import datetime, timezone

log = structlog.get_logger(__name__)


class CheckpointService:
    """
    Orchestrates edge-to-cloud checkpoint synchronization, monitoring
    checksum health, storage limits, and recovery actions.
    """

    def __init__(self, graph: Any, event_bus: Any) -> None:
        self._graph = graph
        self._event_bus = event_bus

    async def synchronize_checkpoint(self, device_id: str, checkpoint_data: Dict[str, Any]) -> None:
        """Log or update the checkpoint configuration parameters inside the Graph."""
        now = datetime.now(timezone.utc).isoformat()
        
        node_id = f"checkpoint:{device_id}"
        await self._graph.upsert_node(
            node_id,
            type="checkpoint",
            last_save=now,
            checkpoint_version=checkpoint_data.get("checkpoint_id", 0),
            health="healthy" if checkpoint_data.get("valid", True) else "corrupt",
            storage_usage_pct=checkpoint_data.get("storage_usage_pct", 5),
            recovery_status="nominal",
        )
        
        await self._event_bus.publish("CheckpointSaved", {
            "device_id": device_id,
            "checkpoint_version": checkpoint_data.get("checkpoint_id", 0),
        })

    async def verify_restore(self, device_id: str, checkpoint_id: int) -> bool:
        """Confirm a checkpoint restore action was completed successfully."""
        node_id = f"checkpoint:{device_id}"
        if node_id in self._graph._graph:
            await self._graph.upsert_node(
                node_id,
                last_restore=datetime.now(timezone.utc).isoformat(),
                recovery_status="restored",
            )
            await self._event_bus.publish("CheckpointLoaded", {
                "device_id": device_id,
                "checkpoint_version": checkpoint_id,
            })
            return True
        return False
