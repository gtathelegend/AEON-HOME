# core/registry/knowledge_base.py

from __future__ import annotations

import structlog
from typing import Any, Dict

log = structlog.get_logger(__name__)


class RuntimeKnowledgeBase:
    """
    Authority combining active context, inferred activities, active policies,
    historical memory stores, and device registries into a unified graph/model.
    """

    def __init__(
        self,
        context_engine: Any,
        activity_engine: Any,
        profile_engine: Any,
        policy_engine: Any,
        cognitive_memory: Any,
        device_registry: Any,
    ) -> None:
        self.context_engine = context_engine
        self.activity_engine = activity_engine
        self.profile_engine = profile_engine
        self.policy_engine = policy_engine
        self.cognitive_memory = cognitive_memory
        self.device_registry = device_registry

    async def get_summary(self) -> Dict[str, Any]:
        """Compile a complete runtime snapshot of the system's state."""
        ctx = await self.context_engine.get_current_context() if self.context_engine else {}
        current_activity = self.activity_engine._current_activity if self.activity_engine else None
        
        user_id = ctx.get("user", {}).get("active_user_id", "default_user")
        profile = await self.profile_engine.get_profile(user_id) if self.profile_engine else {}
        
        memory_stats = self.cognitive_memory.get_statistics() if self.cognitive_memory else {}
        devices = await self.device_registry.get_all_devices() if self.device_registry else []

        active_policies = []
        if self.policy_engine and hasattr(self.policy_engine, "policy_pipeline"):
            for p in self.policy_engine.policy_pipeline._policies:
                active_policies.append({
                    "id": p.identifier,
                    "priority": p.priority,
                    "enabled": getattr(p, "enabled", True),
                })

        return {
            "context": ctx,
            "activity": current_activity,
            "profile": profile,
            "memory_statistics": memory_stats,
            "connected_devices": [
                {
                    "id": d.get("id"),
                    "device_type": d.get("device_type"),
                    "health": d.get("health", "unknown"),
                    "reliability": d.get("reliability", 1.0),
                }
                for d in devices
            ],
            "active_policies": active_policies,
        }
