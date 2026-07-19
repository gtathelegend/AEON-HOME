"""
tests/test_adaptive_intelligence.py — Tests for adaptive intelligence subsystems.

Covers:
  - ContextEngine: provider registration, unified context retrieval
  - ContextAggregator: normalization, validation, overrides
  - ActivityEngine: heuristic classification, history, transition stability
  - ProfileEngine: load preferences, update preference confidence & manual count
  - PolicyEnginePipeline: deterministic ranking, conflict resolution, Decision format
"""
from __future__ import annotations

import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.context.engine import ContextEngine
from core.context.providers import (
    TimeContextProvider,
    SensorContextProvider,
    DeviceContextProvider,
    UserContextProvider,
    SystemContextProvider,
    RuntimeContextProvider,
)
from core.context.aggregator import ContextAggregator, ImmutableContext
from core.reasoning.activity_engine import ActivityEngine
from core.profiles.profile_engine import ProfileEngine
from core.policy.policy_engine import PolicyEnginePipeline


# ── Context Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_context_aggregation_and_lifecycle() -> None:
    ws_bus = MagicMock()
    ws_bus.sensor_processor = MagicMock()
    ws_bus.sensor_processor.get_latest = MagicMock(return_value={
        "temperature": 26.5,
        "humidity": 62.0,
        "motion": True,
        "door_open": False,
        "mean_temp": 25.0,
        "var_temp": 0.2,
        "delta_motion": 1.5,
    })
    ws_bus.serial_bridge = MagicMock()
    ws_bus.serial_bridge.get_status = MagicMock(return_value={"connected": True, "port": "COM3"})
    ws_bus.device_registry = MagicMock()
    ws_bus.device_registry.list_devices = MagicMock(return_value=[{"id": "sentinel_01"}])
    ws_bus.identity_manager = AsyncMock()
    ws_bus.identity_manager.list_users = AsyncMock(return_value=[{"id": "owner_id"}])
    ws_bus.model_manager = MagicMock()
    ws_bus.model_manager.get_deployment_status = MagicMock(return_value={
        "active_model": {"model_id": "anomaly_detector", "version": 2}
    })
    ws_bus.model_manager.runtime_statistics = MagicMock()
    ws_bus.model_manager.runtime_statistics.to_dict = MagicMock(return_value={
        "avg_confidence": 0.91,
        "total_inference_count": 100,
        "error_count": 0,
    })

    engine = ContextEngine(ws_bus=ws_bus)
    engine.register_provider("temporal", TimeContextProvider())
    engine.register_provider("environmental", SensorContextProvider(ws_bus=ws_bus))
    engine.register_provider("device", DeviceContextProvider(ws_bus=ws_bus))
    engine.register_provider("user", UserContextProvider(ws_bus=ws_bus))
    engine.register_provider("system", SystemContextProvider())
    engine.register_provider("runtime", RuntimeContextProvider(ws_bus=ws_bus))

    ctx = await engine.get_current_context()
    
    assert ctx["environmental"]["temperature"] == 26.5
    assert ctx["environmental"]["humidity"] == 62.0
    assert ctx["environmental"]["motion"] is True
    assert ctx["device"]["serial_connected"] is True
    assert ctx["user"]["active_user_id"] == "owner_id"
    assert ctx["runtime"]["active_model_id"] == "anomaly_detector"
    assert ctx["runtime"]["active_model_version"] == 2


@pytest.mark.asyncio
async def test_context_validation_clamps() -> None:
    aggregator = ContextAggregator()
    providers = {
        "environmental": MagicMock(get_context=AsyncMock(return_value={
            "temperature": 150.0,  # exceeds bounds
            "humidity": -20.0,    # exceeds bounds
        }))
    }
    
    frozen_ctx = await aggregator.aggregate(providers, overrides={})
    assert frozen_ctx.environmental["temperature"] == 85.0
    assert frozen_ctx.environmental["humidity"] == 0.0


# ── Activity Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_inference_sleeping() -> None:
    engine = ActivityEngine()
    context = {
        "environmental": {"motion": False},
        "temporal": {"hour": 23, "is_weekend": False},
    }
    act = await engine.infer_current_activity(context)
    assert act["activity"] == "Sleeping"
    assert act["confidence"] == 0.85


@pytest.mark.asyncio
async def test_activity_inference_working() -> None:
    engine = ActivityEngine()
    context = {
        "environmental": {"motion": True},
        "temporal": {"hour": 10, "is_weekend": False},
    }
    act = await engine.infer_current_activity(context)
    assert act["activity"] == "Working"
    assert act["confidence"] == 0.80


@pytest.mark.asyncio
async def test_activity_transition_history() -> None:
    engine = ActivityEngine()
    
    ctx1 = {"environmental": {"motion": True}, "temporal": {"hour": 10, "is_weekend": False}}
    ctx2 = {"environmental": {"motion": False}, "temporal": {"hour": 23, "is_weekend": False}}
    
    await engine.infer_current_activity(ctx1)
    await engine.infer_current_activity(ctx2)
    
    history = engine.get_history()
    # Transition finalized ctx1 into history
    assert len(history) >= 1
    assert history[0]["activity"] == "Working"
    assert history[0]["transition_reason"] == "switched_to_Sleeping"


# ── Profile Engine Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profile_engine_adaptation_and_confidence() -> None:
    graph = AsyncMock()
    graph._graph = MagicMock()
    
    # Simulate first load (no existing preferences)
    engine = ProfileEngine(graph=graph)
    profile = await engine.get_profile("test_user")
    
    assert profile["identity"] == "test_user"
    assert profile["preferences"]["preferred_temperature"]["current_value"] == 21.0
    assert profile["preferences"]["preferred_temperature"]["confidence"] == 1.0

    # Record manual override signal
    await engine.record_signal("test_user", "preferred_temperature", 24.5, "manual_override")
    
    # Verify graph update call
    assert graph.upsert_node.called
    node_args = graph.upsert_node.call_args[1]
    assert node_args["current_value"] == 24.5
    assert node_args["manual_count"] == 1
    assert node_args["confidence"] < 1.0  # confidence reduced on contradiction


# ── Policy Engine Pipeline Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_policy_pipeline_ranked_resolution() -> None:
    pipeline = PolicyEnginePipeline()
    
    # Construct input states
    context = {
        "environmental": {"temperature": 52.0, "motion": False},  # triggers Emergency (> 50)
        "temporal": {"hour": 12},
        "runtime": {"active_model_version": 4},
        "behavioral": {"recent_overrides": {}},
    }
    activity = {"activity": "Idle"}
    profile = {"preferences": {}}
    
    decision = await pipeline.evaluate_policies(
        context=context,
        activity=activity,
        profile=profile,
        system_state={},
        model_output={},
    )
    
    # EmergencyPolicy priority 8 must override everything
    assert decision["selected_policy"] == "emergency_policy"
    assert decision["requested_action"] == "notify"
    assert "CRITICAL_TEMPERATURE" in decision["reason"]
    assert decision["priority"] == 8


@pytest.mark.asyncio
async def test_policy_pipeline_override_resolution() -> None:
    pipeline = PolicyEnginePipeline()
    
    context = {
        "environmental": {"temperature": 21.0, "motion": True},
        "temporal": {"hour": 12},
        "runtime": {"active_model_version": 4},
        "behavioral": {"recent_overrides": {"relay_1_state": True}}, # triggers UserOverride (Priority 5)
    }
    activity = {"activity": "Working"}
    profile = {"preferences": {}}
    
    decision = await pipeline.evaluate_policies(
        context=context,
        activity=activity,
        profile=profile,
        system_state={},
        model_output={},
    )
    
    assert decision["selected_policy"] == "user_override_policy"
    assert decision["requested_action"] == "actuate_fan"
    assert decision["priority"] == 5
