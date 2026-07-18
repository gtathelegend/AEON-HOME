# backend/aeon/services/recommendation_service.py

from __future__ import annotations

import uuid
import structlog
from typing import Any, Dict, List
from datetime import datetime, timezone

log = structlog.get_logger(__name__)


class RecommendationService:
    """Service layer managing suggest routines, comfort preferences, and approvals."""

    def __init__(self, graph: Any, event_bus: Any) -> None:
        self._graph = graph
        self._event_bus = event_bus

    async def generate_recommendation(self, user_id: str, description: str, setting: str, proposed_value: Any) -> Dict[str, Any]:
        """Produce an explainable recommendation and store it in the Graph."""
        rec_id = f"rec:{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()

        rec_data = {
            "rec_id": rec_id,
            "user_id": user_id,
            "description": description,
            "setting": setting,
            "proposed_value": proposed_value,
            "status": "pending",  # pending, approved, rejected
            "created_at": now,
        }

        await self._graph.upsert_node(rec_id, type="recommendation", **rec_data)
        
        await self._event_bus.publish("RecommendationGenerated", rec_data)
        log.info("recommendation.generated", rec_id=rec_id)
        
        return rec_data

    async def respond_to_recommendation(self, rec_id: str, approved: bool) -> bool:
        """Approve or reject a recommendation."""
        if rec_id not in self._graph._graph:
            return False

        status = "approved" if approved else "rejected"
        await self._graph.upsert_node(rec_id, status=status)
        log.info("recommendation.response_recorded", rec_id=rec_id, status=status)
        return True
