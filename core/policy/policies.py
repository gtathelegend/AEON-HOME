# core/policy/policies.py

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Optional
import uuid

from core.interfaces.adaptive import IPolicy


class BasePolicy(IPolicy):
    """Abstract base class for system policies."""

    def __init__(self, identifier: str, priority: int, enabled: bool = True) -> None:
        self._id = identifier
        self._priority = priority
        self._enabled = enabled
        self._history: list[Dict[str, Any]] = []

    @property
    def identifier(self) -> str:
        return self._id

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def enabled(self) -> bool:
        return self._enabled

    def record_execution(self, decision: Dict[str, Any]) -> None:
        self._history.append(decision)
        if len(self._history) > 20:
            self._history.pop(0)


class EmergencyPolicy(BasePolicy):
    """Priority 8: Critical safety emergencies (e.g. fire/sensor limits)."""

    def __init__(self) -> None:
        super().__init__("emergency_policy", priority=8)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        env = context.get("environmental", {})
        temp = env.get("temperature", 21.0)
        # If temp is dangerously high (> 50C)
        if temp > 50.0:
            return {
                "action": "notify",
                "reason": f"CRITICAL_TEMPERATURE_EMERGENCY: {temp}°C",
                "confidence": 1.0,
                "suggested_action": "sound_buzzer",
            }
        return None


class SafetyPolicy(BasePolicy):
    """Priority 7: Equipment protection and occupant safety rules."""

    def __init__(self) -> None:
        super().__init__("safety_policy", priority=7)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        env = context.get("environmental", {})
        temp = env.get("temperature", 21.0)
        # Prevent freezing / overheating equipment
        if temp < 5.0:
            return {
                "action": "actuate_fan",
                "fan_speed": 100,
                "reason": f"FREEZE_PROTECTION_TRIGGERED: {temp}°C",
                "confidence": 0.95,
                "suggested_action": "turn_on_heating",
            }
        return None


class SecurityPolicy(BasePolicy):
    """Priority 6: Security and intrusion alert rules."""

    def __init__(self) -> None:
        super().__init__("security_policy", priority=6)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        env = context.get("environmental", {})
        act_name = activity.get("activity", "Idle")
        # If motion detected while house is Away
        if env.get("motion", False) and act_name == "Away":
            return {
                "action": "notify",
                "reason": "SECURITY_ALERT: Motion detected while Away",
                "confidence": 0.90,
                "suggested_action": "alert_user",
            }
        return None


class UserOverridePolicy(BasePolicy):
    """Priority 5: Direct user interventions (e.g. voice/dashboard overrides)."""

    def __init__(self) -> None:
        super().__init__("user_override_policy", priority=5)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        beh = context.get("behavioral", {})
        overrides = beh.get("recent_overrides", {})
        if "fan_speed" in overrides:
            val = overrides["fan_speed"]
            return {
                "action": "actuate_fan",
                "fan_speed": val,
                "reason": f"USER_OVERRIDE_FAN: {val}%",
                "confidence": 1.0,
                "suggested_action": "fan_speed_adjust",
            }
        elif "relay_1_state" in overrides:
            val = overrides["relay_1_state"]
            return {
                "action": "actuate_fan",
                "fan_speed": 100 if val else 0,
                "reason": f"USER_OVERRIDE_RELAY: {val}",
                "confidence": 1.0,
                "suggested_action": "relay_actuate",
            }
        return None


class ComfortPolicy(BasePolicy):
    """Priority 4: Climate rules reflecting user profile preferred temperature."""

    def __init__(self) -> None:
        super().__init__("comfort_policy", priority=4)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        env = context.get("environmental", {})
        temp = env.get("temperature", 21.0)
        
        pref = profile.get("preferences", {}).get("preferred_temperature", {})
        pref_temp = pref.get("current_value", 21.0)
        pref_conf = pref.get("confidence", 1.0)

        # comfort vs energy policy
        comfort_pref = profile.get("preferences", {}).get("comfort_preference", {})
        comfort_mode = comfort_pref.get("current_value", "comfort")

        if comfort_mode == "comfort" and abs(temp - pref_temp) > 3.0:
            deviation = temp - pref_temp
            speed = min(100, max(0, int(deviation * 20)))
            return {
                "action": "actuate_fan",
                "fan_speed": speed,
                "reason": f"COMFORT_CLIMATE_DEVIATION: temp={temp}°C (pref={pref_temp}°C)",
                "confidence": pref_conf,
                "suggested_action": "climate_adjust",
            }
        return None


class AutomationPolicy(BasePolicy):
    """Priority 3: Graph-implied rule rules (legacy compliance)."""

    def __init__(self) -> None:
        super().__init__("automation_policy", priority=3)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        # Evaluate using QNN model outputs or graph rules
        # Handled at the pipeline level by integrating model_output
        return None


class OptimizationPolicy(BasePolicy):
    """Priority 2: Energy-saving and system optimization rules."""

    def __init__(self) -> None:
        super().__init__("optimization_policy", priority=2)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        act_name = activity.get("activity", "Idle")
        # If sleeping/away, enable eco mode
        if act_name in ("Sleeping", "Away"):
            return {
                "action": "actuate_fan",
                "fan_speed": 0,
                "reason": f"OPTIMIZATION_ECO_MODE: activity={act_name}",
                "confidence": 0.80,
                "suggested_action": "eco_saving",
            }
        return None


class BackgroundPolicy(BasePolicy):
    """Priority 1: Fallback default rules."""

    def __init__(self) -> None:
        super().__init__("background_policy", priority=1)

    async def evaluate(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return {
            "action": "no_action",
            "reason": "NOMINAL_BACKGROUND_FALLBACK",
            "confidence": 0.50,
            "suggested_action": "idle",
        }
