# core/profiles/profile_engine.py

from __future__ import annotations

import time
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.interfaces.adaptive import IProfileEngine, IProfileStore

log = structlog.get_logger(__name__)


class ProfileEngine(IProfileEngine):
    """
    Manages user profiles and adaptive preferences.
    Saves and loads preferences from the Knowledge Graph.
    Records manual corrections/overrides as learning signals.
    """

    def __init__(self, graph: Any, ws_bus: Any = None) -> None:
        self._graph = graph
        self._ws_bus = ws_bus
        self._default_preferences = {
            "preferred_temperature": 21.0,
            "preferred_brightness": 75.0,
            "preferred_fan_speed": 3.0,
            "preferred_schedule": "09:00-17:00",
            "comfort_preference": "comfort",
        }

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Load and return the complete profile snapshot for a user."""
        preferences = {}
        
        # Load from graph if user exists
        for setting, default_val in self._default_preferences.items():
            node_id = f"pref:{user_id}:{setting}"
            node_data = {}
            if node_id in self._graph._graph:
                node_data = self._graph._graph.nodes[node_id]

            # Reconstruct adaptive preference model structure
            preferences[setting] = {
                "current_value": node_data.get("current_value", default_val),
                "confidence": float(node_data.get("confidence", 1.0)),
                "source": node_data.get("source", "system_default"),
                "last_modified": node_data.get("last_modified", datetime.now(timezone.utc).isoformat()),
                "manual_count": int(node_data.get("manual_count", 0)),
                "automatic_count": int(node_data.get("automatic_count", 0)),
                "learning_weight": float(node_data.get("learning_weight", 1.0)),
                "history_size": int(node_data.get("history_size", 0)),
            }

        profile_metadata = {
            "identity": user_id,
            "preferences": preferences,
            "adaptive_weight": 0.80,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }
        return profile_metadata

    async def record_signal(
        self,
        user_id: str,
        setting: str,
        value: Any,
        source: str,
    ) -> None:
        """
        Record manual overrides/corrections as learning signals.
        Gradually adapts preference confidence and counts.
        """
        if setting not in self._default_preferences:
            log.warning("profile.unknown_setting", setting=setting)
            return

        node_id = f"pref:{user_id}:{setting}"
        node_data = {
            "current_value": self._default_preferences[setting],
            "confidence": 1.0,
            "source": "system_default",
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "manual_count": 0,
            "automatic_count": 0,
            "learning_weight": 1.0,
            "history_size": 0,
        }

        # Load existing preference node attributes
        if node_id in self._graph._graph:
            existing = self._graph._graph.nodes[node_id]
            for k in node_data:
                if k in existing:
                    node_data[k] = existing[k]

        # Update metadata based on signal source
        node_data["current_value"] = value
        node_data["last_modified"] = datetime.now(timezone.utc).isoformat()
        node_data["source"] = source
        node_data["history_size"] += 1

        if source in ("manual_override", "user_correction"):
            node_data["manual_count"] += 1
            # Lower confidence when override contradicts current preference setting
            node_data["confidence"] = max(0.1, node_data["confidence"] - 0.1)
        else:
            node_data["automatic_count"] += 1
            # Slowly build confidence back up
            node_data["confidence"] = min(1.0, node_data["confidence"] + 0.05)

        # Save back to graph database
        await self._graph.upsert_node(node_id, type="preference", setting=setting, **node_data)
        # Link user node to preference node
        await self._graph.upsert_edge(user_id, node_id, rel="prefers", value=value)

        log.info(
            "profile.learning_signal_recorded",
            user_id=user_id,
            setting=setting,
            value=value,
            confidence=node_data["confidence"],
            manual_count=node_data["manual_count"],
        )

        if self._ws_bus:
            try:
                profile = await self.get_profile(user_id)
                await self._ws_bus.publish("profile_update", profile)
            except Exception:
                pass
