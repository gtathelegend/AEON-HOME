# backend/aeon/services/preference_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict

log = structlog.get_logger(__name__)


class PreferenceService:
    """Service layer managing user preferences, confidence indices, and adaptations."""

    def __init__(self, profile_engine: Any, event_bus: Any) -> None:
        self._engine = profile_engine
        self._event_bus = event_bus

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        if not self._engine:
            return {}
        return await self._engine.get_profile(user_id)

    async def update_preference(self, user_id: str, setting: str, value: Any, source: str = "api") -> None:
        if not self._engine:
            return
        await self._engine.record_signal(user_id, setting, value, source)
        await self._event_bus.publish("PreferenceUpdated", {
            "user_id": user_id,
            "setting": setting,
            "value": value,
        })
