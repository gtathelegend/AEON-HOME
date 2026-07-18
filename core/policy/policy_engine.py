# core/policy/policy_engine.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import structlog
from typing import Any, Dict, List, Optional

from core.interfaces.adaptive import IPolicyEngine, IPolicy
from core.policy.policies import (
    EmergencyPolicy,
    SafetyPolicy,
    SecurityPolicy,
    UserOverridePolicy,
    ComfortPolicy,
    AutomationPolicy,
    OptimizationPolicy,
    BackgroundPolicy,
)

log = structlog.get_logger(__name__)


class PolicyEnginePipeline(IPolicyEngine):
    """
    Independent policy execution pipeline.
    Runs the lifecycle: Collect -> Validate -> Rank -> Evaluate -> Resolve Conflicts -> Produce Decision -> Publish.
    """

    def __init__(self, ws_bus: Any = None) -> None:
        self._ws_bus = ws_bus
        self._policies: List[IPolicy] = [
            EmergencyPolicy(),
            SafetyPolicy(),
            SecurityPolicy(),
            UserOverridePolicy(),
            ComfortPolicy(),
            AutomationPolicy(),
            OptimizationPolicy(),
            BackgroundPolicy(),
        ]
        self._decision_history: List[Dict[str, Any]] = []

    async def evaluate_policies(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
        system_state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes the policy pipeline.
        Returns a rich Decision object.
        """
        # ── 1. Collect & Validate ──
        active_policies = [p for p in self._policies if getattr(p, "enabled", True)]

        # ── 2. Rank (Deterministic Sort by priority, highest first) ──
        ranked_policies = sorted(active_policies, key=lambda p: p.priority, reverse=True)

        # ── 3. Evaluate & Resolve Conflicts ──
        selected_policy: Optional[IPolicy] = None
        decision_payload: Optional[Dict[str, Any]] = None
        conflict_log: List[str] = []

        for policy in ranked_policies:
            # Handle legacy/implied rules for AutomationPolicy
            if isinstance(policy, AutomationPolicy):
                # If model says anomaly exists or presence is high, fire automation
                presence_prob = model_output.get("presence_prob", 0.0)
                anomaly_score = model_output.get("anomaly_score", 0.0)
                if anomaly_score > 0.85:
                    decision_payload = {
                        "action": "notify",
                        "reason": f"AUTOMATION_ANOMALY_ALARM: score={anomaly_score:.2f}",
                        "confidence": anomaly_score,
                        "suggested_action": "sound_buzzer",
                    }
                    selected_policy = policy
                    break
                elif presence_prob > 0.75:
                    decision_payload = {
                        "action": "notify",
                        "reason": f"AUTOMATION_PRESENCE_DETECTED: prob={presence_prob:.2f}",
                        "confidence": presence_prob,
                        "suggested_action": "sound_buzzer",
                    }
                    selected_policy = policy
                    break
                continue

            # Standard policy evaluate
            res = await policy.evaluate(context, activity, profile)
            if res:
                # High priority match found. Since list is sorted by priority,
                # the first policy to return a payload wins (conflict resolved).
                selected_policy = policy
                decision_payload = res
                break
            else:
                conflict_log.append(f"Policy '{policy.identifier}' evaluated to None")

        # Fallback to BackgroundPolicy if no policy triggers
        if not selected_policy or not decision_payload:
            selected_policy = ranked_policies[-1]  # background
            decision_payload = {
                "action": "no_action",
                "reason": "NOMINAL_BACKGROUND_FALLBACK",
                "confidence": 0.50,
                "suggested_action": "idle",
            }

        # ── 4. Produce Decision Object ──
        decision_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        decision = {
            "decision_id": decision_id,
            "timestamp": timestamp,
            "selected_policy": selected_policy.identifier,
            "supporting_context": context,
            "activity": activity.get("activity", "Idle"),
            "confidence": decision_payload.get("confidence", 0.5),
            "priority": selected_policy.priority,
            "target_device": "relay_1" if "relay" in decision_payload.get("action", "") else "buzzer",
            "requested_action": decision_payload.get("action", "no_action"),
            "reason": decision_payload.get("reason", "nominal"),
            "suggested_action": decision_payload.get("suggested_action", "idle"),
            "model_version": context.get("runtime", {}).get("active_model_version", 0),
            "conflict_log": conflict_log,
        }

        # Record in policy execution history
        if hasattr(selected_policy, "record_execution"):
            selected_policy.record_execution(decision)

        self._decision_history.append(decision)
        if len(self._decision_history) > 100:
            self._decision_history.pop(0)

        # ── 5. Publish Decision ──
        await self._publish_decision(decision)

        return decision

    async def _publish_decision(self, decision: Dict[str, Any]) -> None:
        if self._ws_bus:
            try:
                await self._ws_bus.publish("decision_update", decision)
            except Exception:
                pass
        log.info(
            "policy.decision_produced",
            decision_id=decision["decision_id"],
            policy=decision["selected_policy"],
            action=decision["requested_action"],
            reason=decision["reason"],
        )
