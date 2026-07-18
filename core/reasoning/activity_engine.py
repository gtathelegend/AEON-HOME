# core/reasoning/activity_engine.py

from __future__ import annotations

import time
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.interfaces.adaptive import IActivityEngine

log = structlog.get_logger(__name__)


class ActivityEngine(IActivityEngine):
    """
    Infers semantic activities (Sleeping, Working, Idle, etc.) based on
    environmental, temporal, behavioral, and device context.
    Tracks a rolling history of inferred activities and their durations.
    """

    def __init__(self, ws_bus: Any = None) -> None:
        self._ws_bus = ws_bus
        self._history: List[Dict[str, Any]] = []
        self._max_history = 50
        self._current_activity: Optional[Dict[str, Any]] = None

    async def infer_current_activity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the inference rules on context and updates/records the activity."""
        env = context.get("environmental", {})
        temp = context.get("temporal", {})
        dev = context.get("device", {})
        beh = context.get("behavioral", {})

        hour = temp.get("hour", 12)
        motion = env.get("motion", False)
        temp_val = env.get("temperature", 21.0)
        is_weekend = temp.get("is_weekend", False)

        # ── Simple heuristic rule-based classifier ──
        activity_name = "Idle"
        confidence = 0.50
        evidence = {}

        if not motion:
            if 22 <= hour or hour <= 6:
                activity_name = "Sleeping"
                confidence = 0.85
                evidence = {"motion": False, "hour": f"{hour}:00"}
            else:
                activity_name = "Away"
                confidence = 0.70
                evidence = {"motion": False, "hour": f"{hour}:00"}
        else:
            if 8 <= hour <= 17 and not is_weekend:
                activity_name = "Working"
                confidence = 0.80
                evidence = {"motion": True, "working_hours": True}
            elif 17 < hour <= 22:
                # Evening activities
                activity_name = "Watching TV"
                confidence = 0.75
                evidence = {"motion": True, "evening": True}
            elif (11 <= hour <= 13) or (18 <= hour <= 20):
                activity_name = "Cooking"
                confidence = 0.65
                evidence = {"motion": True, "mealtime": True}
            else:
                activity_name = "Relaxing"
                confidence = 0.60
                evidence = {"motion": True}

        now_epoch = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate prediction stability (based on transition or historical confidence variance)
        stability = 1.0
        duration = 0.0

        if self._current_activity and self._current_activity["activity"] == activity_name:
            duration = now_epoch - self._current_activity["start_epoch"]
            # Confidence trend / stability
            stability = max(0.0, min(1.0, 1.0 - abs(confidence - self._current_activity["confidence"])))
            # Keep same start time
            start_epoch = self._current_activity["start_epoch"]
            start_time = self._current_activity["start_time"]
            trend = confidence - self._current_activity["confidence"]
        else:
            # Transition occurred
            if self._current_activity:
                # Finalize previous activity entry
                self._current_activity["end_time"] = timestamp
                self._current_activity["end_epoch"] = now_epoch
                self._current_activity["duration"] = now_epoch - self._current_activity["start_epoch"]
                self._current_activity["transition_reason"] = f"switched_to_{activity_name}"
                self._push_history(self._current_activity)

            start_epoch = now_epoch
            start_time = timestamp
            trend = 0.0
            log.info("activity.transition", previous=self._current_activity["activity"] if self._current_activity else "None", new=activity_name)

        new_act = {
            "activity": activity_name,
            "confidence": confidence,
            "evidence": evidence,
            "timestamp": timestamp,
            "start_time": start_time,
            "start_epoch": start_epoch,
            "duration": duration,
            "stability": stability,
            "trend": trend,
            "source": "heuristics",
        }

        self._current_activity = new_act

        if self._ws_bus:
            try:
                await self._ws_bus.publish("activity_update", {
                    "activity": activity_name,
                    "confidence": confidence,
                    "duration": duration,
                    "timestamp": timestamp,
                })
            except Exception:
                pass

        return new_act

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        history_copy = [dict(h) for h in self._history]
        # Include current active if not finalized
        if self._current_activity:
            current_copy = dict(self._current_activity)
            current_copy["duration"] = time.time() - current_copy["start_epoch"]
            history_copy.append(current_copy)
        return history_copy[-limit:]

    def _push_history(self, record: Dict[str, Any]) -> None:
        # Keep clean, do not persist unnecessary temporary history fields
        clean_record = {
            "activity": record.get("activity"),
            "start_time": record.get("start_time"),
            "end_time": record.get("end_time"),
            "duration": round(record.get("duration", 0.0), 1),
            "confidence_trend": round(record.get("trend", 0.0), 3),
            "evidence": record.get("evidence"),
            "transition_reason": record.get("transition_reason", "unknown"),
        }
        self._history.append(clean_record)
        if len(self._history) > self._max_history:
            self._history.pop(0)
