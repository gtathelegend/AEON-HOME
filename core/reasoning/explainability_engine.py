# core/reasoning/explainability_engine.py

from __future__ import annotations

import structlog
from typing import Any, Dict, List

from shared.types.models import ExplanationModel, ConfidenceBreakdown

log = structlog.get_logger(__name__)


class ExplainabilityEngine:
    """
    Constructs detailed explanation models for decisions, including
    reason codes, confidence breakdowns, and rejected policy details.
    """

    def explain(
        self,
        decision: Dict[str, Any],
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> ExplanationModel:
        """Analyze a decision and produce a complete ExplanationModel."""
        policy_name = decision["selected_policy"]
        action = decision["requested_action"]
        reason = decision["reason"]
        
        # ── 1. Map Reason Codes ──
        reason_codes = self._map_reason_codes(policy_name, context, activity)

        # ── 2. Compute Confidence Breakdown ──
        conf_breakdown = self._compute_confidence_breakdown(decision, context, activity, profile)

        # ── 3. Draft Human-Readable Summaries ──
        decision_summary = f"System performed '{action}' because {reason}."
        
        evidence_descriptions = [
            e["description"] for e in decision.get("evidence_list", [])
        ]
        evidence_summary = "; ".join(evidence_descriptions) if evidence_descriptions else "No specific sensor evidence recorded."

        rejected = []
        for alt in decision.get("alternative_actions", []):
            if alt["policy"] != policy_name:
                rejected.append(f"Rejected '{alt['action']}' proposed by {alt['policy']} (score: {alt['score']})")

        primary_context = f"Temp: {context.get('environmental', {}).get('temperature', 21.0)}°C, Motion: {context.get('environmental', {}).get('motion', False)}"
        primary_activity = activity.get("activity", "Idle")

        model_contrib = f"Model version {context.get('runtime', {}).get('active_model_version', 0)} reported confidence {context.get('runtime', {}).get('model_confidence', 0.0)}"

        suggested_feedback = "Was this comfort adjustment correct? Reply YES or adjust temperature."

        explanation = ExplanationModel(
            decision_summary=decision_summary,
            evidence_summary=evidence_summary,
            selected_policy=policy_name,
            rejected_policies=rejected,
            primary_context=primary_context,
            primary_activity=primary_activity,
            model_contribution=model_contrib,
            confidence_summary=conf_breakdown,
            reason_codes=reason_codes,
            suggested_user_feedback=suggested_feedback,
            execution_result="command_sent_to_device",
        )

        log.debug("explainability.generated", decision_id=decision.get("decision_id"), codes=reason_codes)

        return explanation

    def _map_reason_codes(self, policy_name: str, context: Dict[str, Any], activity: Dict[str, Any]) -> List[str]:
        codes = []
        if policy_name == "user_override_policy":
            codes.append("MANUAL_OVERRIDE")
        if policy_name == "comfort_policy":
            codes.append("USER_PREFERENCE")
        if policy_name == "security_policy" or policy_name == "emergency_policy":
            codes.append("POLICY_PRIORITY")
        if policy_name == "optimization_policy":
            codes.append("ENERGY_OPTIMIZATION")

        temporal = context.get("temporal", {})
        if temporal.get("hour") in (8, 9, 17, 18, 22, 23):
            codes.append("TIME_BASED")

        if activity.get("confidence", 0.0) > 0.80:
            codes.append("HIGH_CONFIDENCE_ACTIVITY")

        if context.get("runtime", {}).get("model_confidence", 1.0) < 0.40:
            codes.append("LOW_MODEL_CONFIDENCE")

        if not codes:
            codes.append("POLICY_PRIORITY")

        return codes

    def _compute_confidence_breakdown(
        self,
        decision: Dict[str, Any],
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> ConfidenceBreakdown:
        """Deconstructs the reasoning confidence score into components."""
        # Context confidence
        env = context.get("environmental", {})
        ctx_conf = 1.0 if env.get("valid", True) else 0.50

        # Activity confidence
        act_conf = float(activity.get("confidence", 0.50))

        # User profile preference confidence
        pref = profile.get("preferences", {}).get("preferred_temperature", {})
        pref_conf = float(pref.get("confidence", 0.80))

        # Model confidence
        model_conf = float(context.get("runtime", {}).get("model_confidence", 0.85))

        # Reasoning algorithm score (based on alternative entropy / spreads)
        overall = float(decision.get("confidence", 0.50))
        reasoning_conf = round((ctx_conf + act_conf + pref_conf + model_conf) / 4.0, 2)

        return ConfidenceBreakdown(
            context_confidence=ctx_conf,
            activity_confidence=act_conf,
            policy_confidence=pref_conf,  # Represents priority/routine confidence
            model_confidence=model_conf,
            reasoning_confidence=reasoning_conf,
            overall_confidence=overall,
        )
