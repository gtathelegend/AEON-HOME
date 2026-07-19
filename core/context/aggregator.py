# core/context/aggregator.py

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ImmutableContext:
    """Unified read-only context representation."""
    temporal: Dict[str, Any] = field(default_factory=dict)
    environmental: Dict[str, Any] = field(default_factory=dict)
    device: Dict[str, Any] = field(default_factory=dict)
    user: Dict[str, Any] = field(default_factory=dict)
    system: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict)
    behavioral: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temporal": copy.deepcopy(self.temporal),
            "environmental": copy.deepcopy(self.environmental),
            "device": copy.deepcopy(self.device),
            "user": copy.deepcopy(self.user),
            "system": copy.deepcopy(self.system),
            "runtime": copy.deepcopy(self.runtime),
            "behavioral": copy.deepcopy(self.behavioral),
        }


class ContextAggregator:
    """Collects, merges, validates, and freezes context details."""

    async def aggregate(
        self,
        providers: Dict[str, Any],
        overrides: Dict[str, Any],
    ) -> ImmutableContext:
        """
        Runs the context lifecycle:
        1. Collect: Fetch data from all providers
        2. Normalize: Adjust schema / types
        3. Merge: Combine into unified categories + apply overrides
        4. Validate: Validate values are within normal bounds
        5. Freeze: Produce an ImmutableContext
        """
        # ── 1. Collect ──
        raw_data: Dict[str, Dict[str, Any]] = {}
        for category, provider in providers.items():
            try:
                raw_data[category] = await provider.get_context()
            except Exception:
                raw_data[category] = {}

        # ── 2. Normalize & Merge ──
        temporal = raw_data.get("temporal", {})
        environmental = raw_data.get("environmental", {})
        device = raw_data.get("device", {})
        user = raw_data.get("user", {})
        system = raw_data.get("system", {})
        runtime = raw_data.get("runtime", {})
        behavioral = {
            "manual_overrides_count": len(overrides),
            "recent_overrides": copy.deepcopy(overrides),
        }

        # Apply overrides to device/environmental states if relevant
        if "temperature" in overrides:
            environmental["temperature"] = overrides["temperature"]
        if "fan_speed" in overrides:
            device["fan_speed_percent"] = overrides["fan_speed"]
            device["fan_pwm"] = int(overrides["fan_speed"] * 2.55)
        if "relay_1_state" in overrides:
            device["relay_1_state"] = overrides["relay_1_state"]
            device["fan_speed_percent"] = 100 if overrides["relay_1_state"] else 0
            device["fan_pwm"] = 255 if overrides["relay_1_state"] else 0

        # ── 3. Validate ──
        self._validate_environmental(environmental)
        self._validate_device(device)

        # ── 4. Freeze ──
        return ImmutableContext(
            temporal=temporal,
            environmental=environmental,
            device=device,
            user=user,
            system=system,
            runtime=runtime,
            behavioral=behavioral,
        )

    def _validate_environmental(self, env: Dict[str, Any]) -> None:
        # Resolve missing values / clamp
        if "temperature" not in env or env["temperature"] is None:
            env["temperature"] = 21.0
        env["temperature"] = max(-40.0, min(85.0, float(env["temperature"])))

        if "humidity" not in env or env["humidity"] is None:
            env["humidity"] = 50.0
        env["humidity"] = max(0.0, min(100.0, float(env["humidity"])))

        if "motion" not in env:
            env["motion"] = False

    def _validate_device(self, dev: Dict[str, Any]) -> None:
        if "serial_connected" not in dev:
            dev["serial_connected"] = False
        if "fan_speed_percent" not in dev:
            dev["fan_speed_percent"] = 0
        if "fan_pwm" not in dev:
            dev["fan_pwm"] = 0
        if "relay_1_state" not in dev:
            dev["relay_1_state"] = False
