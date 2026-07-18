# core/policy/engine.py

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import numpy as np
from shared.types import FeatureFrame, PolicyDecision

# Subsystem Imports
from core.context.engine import ContextEngine
from core.context.providers import (
    TimeContextProvider,
    SensorContextProvider,
    DeviceContextProvider,
    UserContextProvider,
    SystemContextProvider,
    RuntimeContextProvider,
)
from core.reasoning.activity_engine import ActivityEngine
from core.profiles.profile_engine import ProfileEngine
from core.policy.policy_engine import PolicyEnginePipeline

log = logging.getLogger(__name__)


class PolicyEngine:
    """
    Core decision loop wrapper aligning legacy interfaces with the new
    Context, Activity, User Profile, and Policy Pipeline Engines.
    """

    def __init__(
        self,
        qnn: Any,
        graph: Any,
        memory: Any,
        ws_bus: Any,
        serial_writer: Any,
    ) -> None:
        self._qnn    = qnn
        self._graph  = graph
        self._memory = memory
        self._ws_bus = ws_bus
        self._serial = serial_writer
        self._queue: asyncio.Queue[FeatureFrame] = asyncio.Queue(maxsize=64)

        # ── 1. Context Engine Setup ──
        self.context_engine = ContextEngine(ws_bus=ws_bus)
        self.context_engine.register_provider("temporal", TimeContextProvider())
        self.context_engine.register_provider("environmental", SensorContextProvider(ws_bus=ws_bus))
        self.context_engine.register_provider("device", DeviceContextProvider(ws_bus=ws_bus))
        self.context_engine.register_provider("user", UserContextProvider(ws_bus=ws_bus))
        self.context_engine.register_provider("system", SystemContextProvider())
        self.context_engine.register_provider("runtime", RuntimeContextProvider(ws_bus=ws_bus))

        # ── 2. Activity Engine Setup ──
        self.activity_engine = ActivityEngine(ws_bus=ws_bus)

        # ── 3. User Profile Engine Setup ──
        self.profile_engine = ProfileEngine(graph=graph, ws_bus=ws_bus)

        # ── 4. Policy Engine Pipeline Setup ──
        self.policy_pipeline = PolicyEnginePipeline(ws_bus=ws_bus)

    async def on_feature_frame(self, frame: FeatureFrame) -> None:
        """Called by SerialBridge on every decoded frame. Non-blocking."""
        try:
            self._queue.put_nowait(frame)
        except asyncio.QueueFull:
            log.warning("policy.queue_full — dropping frame", seq=frame.seq)

    async def run(self) -> None:
        """Background consumer — runs inference and dispatches decisions."""
        await self._process_loop()

    async def _process_loop(self) -> None:
        while True:
            frame = await self._queue.get()
            try:
                decision = await self._infer(frame)
                await self._dispatch(decision, frame)
            except Exception:
                log.exception("policy.inference_error")
            finally:
                self._queue.task_done()

    # ── Inference ───────────────

    async def _infer(self, frame: FeatureFrame) -> PolicyDecision:
        start_t = time.perf_counter()

        # ── Step A: Run QNN Models (Maintains NPU verification & mocks) ──
        feature_vec = np.array([[
            frame.temperature, frame.humidity,
            float(frame.motion), float(frame.door_open),
            frame.mean_temp, frame.var_temp, frame.delta_motion,
        ]], dtype=np.float32)

        presence_out = await self._qnn.infer(
            "presence_classifier", {"input": feature_vec}
        )
        presence_prob = float(presence_out.get("output", np.array([[0.5, 0.5]]))[0, 1])

        anomaly_out  = await self._qnn.infer(
            "anomaly_detector", {"input": feature_vec}
        )
        anomaly_score = float(anomaly_out.get("output", np.array([[0.0]]))[0, 0])

        # ── Step B: Execute Context Engine ──
        context = await self.context_engine.get_current_context()

        # ── Step C: Execute Activity Engine ──
        activity = await self.activity_engine.infer_current_activity(context)

        # ── Step D: Execute User Profile Engine ──
        user_id = context.get("user", {}).get("active_user_id", "default_user")
        profile = await self.profile_engine.get_profile(user_id)

        # ── Step E: Execute Policy Pipeline ──
        decision_dict = await self.policy_pipeline.evaluate_policies(
            context=context,
            activity=activity,
            profile=profile,
            system_state={},
            model_output={
                "presence_prob": presence_prob,
                "anomaly_score": anomaly_score,
            },
        )

        latency_ms = (time.perf_counter() - start_t) * 1000

        # Construct compatible PolicyDecision object
        return PolicyDecision(
            action=decision_dict["requested_action"],
            confidence=decision_dict["confidence"],
            reason=decision_dict["reason"],
            frame_seq=frame.seq,
            latency_ms=latency_ms,
        )

    # ── Manual override ───────────────────────────────────────────────────────

    async def execute_override(self, target: str, action: str) -> bool:
        """
        Execute a manual actuation override from the voice assistant.
        Records override signals into Profile and Context engines.
        """
        log.debug("policy.override", target=target, action=action)
        try:
            val_bool = (action == "on" or action is True)

            # Record learning signal in ProfileEngine
            await self.profile_engine.record_signal(
                user_id="default_user",
                setting="preferred_temperature" if target == "temp" else "comfort_preference",
                value=25.0 if val_bool else 18.0,
                source="manual_override",
            )

            # Stage in Context Engine
            await self.context_engine.record_manual_override(
                target="relay_1_state" if target == "relay" else target,
                value=val_bool,
            )

            # Physical actuation
            if target == "relay" or target == "relay_1":
                await self._serial.send_relay(1, val_bool)
            elif target == "buzzer":
                await self._serial.send_buzzer(200 if val_bool else 0)

            await self._memory.log_event("COMMAND", "voice_override", {
                "target": target,
                "action": action,
            })
            await self._ws_bus.publish("policy_updated", {
                "source": "voice_override",
                "target": target,
                "action": action,
            })
            return True
        except Exception:
            log.exception("policy.override_error")
            return False

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(self, decision: PolicyDecision, frame: FeatureFrame) -> None:
        await self._memory.log_decision(decision)
        
        # Publish legacy telemetry to keep dashboard functional
        await self._ws_bus.publish("decision", {
            "action":     decision.action,
            "confidence": decision.confidence,
            "reason":     decision.reason,
            "seq":        decision.frame_seq,
            "latency_ms": decision.latency_ms,
        })
        
        log.debug("policy.decision", action=decision.action,
                  conf=f"{decision.confidence:.2f}", seq=decision.frame_seq,
                  latency_ms=f"{decision.latency_ms:.2f}")

        # Send physical actuation command to firmware
        if decision.action == "notify":
            await self._serial.send_buzzer(200)
        elif decision.action == "actuate_relay":
            await self._serial.send_relay(1, True)
        elif decision.action == "deactivate_relay":
            await self._serial.send_relay(1, False)
