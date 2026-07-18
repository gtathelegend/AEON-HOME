# backend/aeon/services/learning_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict, List
from datetime import datetime, timezone

log = structlog.get_logger(__name__)


class LearningService:
    """
    Subsystem responsible for receiving learning buffers, validating datasets,
    saving training frames, and pushing to the Event Bus.
    """

    def __init__(self, memory: Any, event_bus: Any) -> None:
        self._memory = memory
        self._event_bus = event_bus

    async def upload_buffer_records(self, device_id: str, records: List[Dict[str, Any]]) -> None:
        """Incorporate flushed buffer records from the firmware into the training dataset."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Log to EventMemory and trigger bus events
        for r in records:
            await self._memory.log_event("LEARNING_FRAME", "buffered_record", {
                "device_id": device_id,
                "record": r,
                "received_at": now
            })

        await self._event_bus.publish("LearningUploaded", {
            "device_id": device_id,
            "records_count": len(records),
        })
        log.info("learning.buffer_uploaded", device=device_id, count=len(records))

    async def ingest_feedback(self, feedback_data: Dict[str, Any]) -> None:
        """Process incoming feedback event and log to persistence."""
        await self._memory.log_event("FEEDBACK", feedback_data.get("feedback_type", "unknown"), feedback_data)
        
        await self._event_bus.publish("FeedbackReceived", feedback_data)
        log.info("learning.feedback_received", type=feedback_data.get("feedback_type"))
