# core/policy/engine.py

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import numpy as np
from shared.types import FeatureFrame, PolicyDecision

log = logging.getLogger(__name__)


class PolicyEngine:
    """
    Core decision loop.

    on_feature_frame() is the hot path — called on every serial frame (~2 Hz).
    run() is the background task that processes decisions off the hot path.
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

        feature_vec = np.array([[
            frame.temperature, frame.humidity,
            float(frame.motion), float(frame.door_open),
            frame.mean_temp, frame.var_temp, frame.delta_motion,
        ]], dtype=np.float32)

        # Presence classification
        presence_out = await self._qnn.infer(
            "presence_classifier", {"input": feature_vec}
        )
        presence_prob = float(presence_out.get("output", np.array([[0.5, 0.5]]))[0, 1])

        # Anomaly scoring
        anomaly_out  = await self._qnn.infer(
            "anomaly_detector", {"input": feature_vec}
        )
        anomaly_score = float(anomaly_out.get("output", np.array([[0.0]]))[0, 0])

        # Rule overlay from graph
        rules = self._graph.get_active_rules_sync()
        action, reason = self._apply_rules(
            rules, frame, presence_prob, anomaly_score
        )

        latency_ms = (time.perf_counter() - start_t) * 1000

        return PolicyDecision(
            action=action,
            confidence=max(presence_prob, anomaly_score),
            reason=reason,
            frame_seq=frame.seq,
            latency_ms=latency_ms,
        )

    def _apply_rules(
        self, rules: list, frame: FeatureFrame,
        presence_prob: float, anomaly_score: float,
    ) -> tuple[str, str]:
        if anomaly_score > 0.85:
            return "notify", f"anomaly_score={anomaly_score:.2f}"
        if frame.motion and presence_prob > 0.75:
            return "notify", f"presence_prob={presence_prob:.2f}"
        return "no_action", "nominal"

    # ── Manual override ───────────────────────────────────────────────────────

    async def execute_override(self, target: str, action: str) -> bool:
        """
        Execute a manual actuation override from the voice assistant.
        """
        log.debug("policy.override", target=target, action=action)
        try:
            if action == "on":
                await self._serial.send_relay(1, True)
            else:
                await self._serial.send_relay(1, False)

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
        
        # Publish telemetry
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

        # Send physical actuation if needed
        if decision.action == "notify":
            await self._serial.send_buzzer(200)
        elif decision.action == "actuate_relay":
            await self._serial.send_relay(1, True)
