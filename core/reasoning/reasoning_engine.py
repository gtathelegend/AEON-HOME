# core/reasoning/reasoning_engine.py

from __future__ import annotations

import uuid
import time
from datetime import datetime, timezone
import structlog
from typing import Any, Dict, List, Tuple

from core.reasoning.decision_graph import DecisionGraph
from shared.types.models import EvidenceItem, AlternativeAction

log = structlog.get_logger(__name__)


class ReasoningEngine:
    """
    Evaluates alternative candidate decisions, collects supporting evidence,
    ranks them dynamically, and produces the finalized Decision object.
    """

    def __init__(self) -> None:
        self.decision_graph = DecisionGraph()

    async def reason(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
        policies: List[Any],
        candidate_decisions: List[Dict[str, Any]],
        model_output: Dict[str, Any],
        device_registry: Any,
    ) -> Dict[str, Any]:
        """
        Runs the reasoning lifecycle:
        1. Add nodes and edges to the decision DAG
        2. Gather evidence items
        3. Score and rank alternative actions
        4. Select winner and pack Decision Object
        """
        # Resolve target device capabilities
        device_caps = {"relay_actuate": True, "buzzer_notify": True}
        devices = await device_registry.get_all_devices() if device_registry else []
        
        # Build DAG
        self.decision_graph.build_graph(
            context=context,
            activity=activity,
            profile=profile,
            policies=policies,
            model_output=model_output,
            device_caps=device_caps,
        )

        # ── 1. Gather Evidence ──
        evidence_list = self._collect_evidence(context, activity, profile, model_output)

        # ── 2. Rank Alternatives ──
        alternatives = self._rank_alternatives(
            candidate_decisions,
            context,
            activity,
            profile,
            evidence_list,
            devices
        )

        # Select winner
        winning_alt = alternatives[0] if alternatives else AlternativeAction(
            action="no_action",
            score=0.50,
            policy="background_policy",
            reason="NOMINAL_BACKGROUND_FALLBACK",
        )

        # ── 3. Finalize Decision Object ──
        decision_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Find fan speed from winning candidate
        fan_speed = 0
        for cand in candidate_decisions:
            if cand.get("action") == winning_alt.action and cand.get("policy") == winning_alt.policy:
                fan_speed = cand.get("fan_speed", 0)
                break

        # Determine target device and outcome
        if "fan" in winning_alt.action or "relay" in winning_alt.action:
            target_device = "fan"
            expected_outcome = "fan_speed_adjusted"
        else:
            target_device = "buzzer" if "notify" in winning_alt.action else "system_idle"
            expected_outcome = "alarm_sounded" if "notify" in winning_alt.action else "system_idle"

        decision = {
            "decision_id": decision_id,
            "timestamp": timestamp,
            "selected_policy": winning_alt.policy,
            "requested_action": winning_alt.action,
            "fan_speed": fan_speed,
            "reason": winning_alt.reason,
            "confidence": winning_alt.score,
            "priority": self._get_policy_priority(winning_alt.policy, policies),
            "target_device": target_device,
            "supporting_context": context,
            "activity": activity.get("activity", "Idle"),
            "model_version": context.get("runtime", {}).get("active_model_version", 0),
            "evidence_list": [e.to_dict() for e in evidence_list],
            "alternative_actions": [a.to_dict() for a in alternatives],
            "reasoning_trace": self.decision_graph.get_influences(f"policy:{winning_alt.policy}"),
            "expected_outcome": expected_outcome,
            "execution_status": "pending",
        }

        log.info(
            "reasoning.completed",
            decision_id=decision_id,
            action=winning_alt.action,
            policy=winning_alt.policy,
            score=winning_alt.score,
        )

        return decision

    def _collect_evidence(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> List[EvidenceItem]:
        evidence = []
        now = datetime.now(timezone.utc).isoformat()

        # Motion evidence
        env = context.get("environmental", {})
        if env.get("motion", False):
            evidence.append(EvidenceItem(
                source="environmental_sensors",
                timestamp=now,
                weight=0.90,
                confidence=1.0,
                reliability=0.95,
                description="Motion detected in room",
            ))

        # Temperature deviation
        temp = env.get("temperature", 21.0)
        pref_temp = profile.get("preferences", {}).get("preferred_temperature", {}).get("current_value", 21.0)
        if abs(temp - pref_temp) > 3.0:
            evidence.append(EvidenceItem(
                source="comfort_deviation",
                timestamp=now,
                weight=0.85,
                confidence=profile.get("preferences", {}).get("preferred_temperature", {}).get("confidence", 0.8),
                reliability=0.90,
                description=f"Temperature {temp}°C deviates from preferred {pref_temp}°C",
            ))

        # User overrides
        beh = context.get("behavioral", {})
        if beh.get("recent_overrides"):
            evidence.append(EvidenceItem(
                source="user_override",
                timestamp=now,
                weight=1.0,
                confidence=1.0,
                reliability=1.0,
                description=f"Active user manual override: {list(beh['recent_overrides'].keys())}",
            ))

        # Active Activity
        act_name = activity.get("activity", "Idle")
        if act_name != "Idle":
            evidence.append(EvidenceItem(
                source="activity_inferred",
                timestamp=now,
                weight=0.75,
                confidence=activity.get("confidence", 0.5),
                reliability=0.85,
                description=f"Current user activity inferred as {act_name}",
            ))

        # Anomaly scoring
        anomaly_score = model_output.get("anomaly_score", 0.0)
        if anomaly_score > 0.85:
            evidence.append(EvidenceItem(
                source="anomaly_detector",
                timestamp=now,
                weight=0.95,
                confidence=anomaly_score,
                reliability=0.90,
                description=f"Inference model flagged temperature anomaly: score={anomaly_score:.2f}",
            ))

        return evidence

    def _rank_alternatives(
        self,
        candidate_decisions: List[Dict[str, Any]],
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
        evidence_list: List[EvidenceItem],
        devices: List[Dict[str, Any]]
    ) -> List[AlternativeAction]:
        """Rank actions: ON, OFF, Unchanged, Delay action, Notify user."""
        ranked = []
        
        # Pull device reliability if available
        device_rel = 1.0
        if devices:
            device_rel = float(devices[0].get("reliability", 1.0))

        for cand in candidate_decisions:
            action = cand["action"]
            policy_name = cand["policy"]
            reason = cand["reason"]
            base_conf = cand.get("confidence", 0.5)
            priority = cand.get("priority", 1)

            # Scoring weight components: Priority (40%), Base Confidence (30%), Device Reliability (15%), Evidence coverage (15%)
            priority_score = priority / 8.0
            evidence_cov = len(evidence_list) / 5.0 if evidence_list else 0.2
            
            score = (
                priority_score * 0.40 +
                base_conf * 0.30 +
                device_rel * 0.15 +
                evidence_cov * 0.15
            )

            ranked.append(AlternativeAction(
                action=action,
                score=round(score, 3),
                policy=policy_name,
                reason=reason,
            ))

        # Sort in descending order of score
        return sorted(ranked, key=lambda a: a.score, reverse=True)

    def _get_policy_priority(self, policy_name: str, policies: List[Any]) -> int:
        for p in policies:
            if p.identifier == policy_name:
                return p.priority
        return 1
