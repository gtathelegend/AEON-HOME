# backend/aeon/services/policy_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict, List

log = structlog.get_logger(__name__)


class PolicyService:
    """Service layer managing policy configurations, priorities, and version-tracking."""

    def __init__(self, policy_engine: Any) -> None:
        self._engine = policy_engine

    def list_policies(self) -> List[Dict[str, Any]]:
        if not self._engine or not hasattr(self._engine, "policy_pipeline"):
            return []
        
        policies = []
        for p in self._engine.policy_pipeline._policies:
            policies.append({
                "identifier": p.identifier,
                "priority": p.priority,
                "enabled": getattr(p, "enabled", True),
            })
        return policies

    async def update_policy_state(self, policy_id: str, enabled: bool) -> bool:
        if not self._engine or not hasattr(self._engine, "policy_pipeline"):
            return False

        for p in self._engine.policy_pipeline._policies:
            if p.identifier == policy_id:
                p.enabled = enabled
                log.info("policy.state_updated", policy=policy_id, enabled=enabled)
                return True
        return False
