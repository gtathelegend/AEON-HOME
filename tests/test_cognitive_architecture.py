"""
tests/test_cognitive_architecture.py — Verification suite for Commit 5 cognitive subsystems.

Covers:
  - ReasoningEngine: ranking alternatives, evidence gathering, DAG construction
  - ExplainabilityEngine: summaries, reason codes, confidence breakdown
  - CognitiveMemory: category storage, query, retention garbage collection
  - DeviceRegistry: capabilities, status, response times, reliability metrics
  - Cognitive API: REST endpoints for decisions, explanations, and memory stats
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from core.reasoning.reasoning_engine import ReasoningEngine
from core.reasoning.explainability_engine import ExplainabilityEngine
from core.memory.cognitive_memory import CognitiveMemory
from core.registry.devices import DeviceRegistry
from core.registry.knowledge_base import RuntimeKnowledgeBase
from backend.aeon.api.app import create_app


# ── Reasoning Engine Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reasoning_engine_decision_ranking() -> None:
    engine = ReasoningEngine()
    
    context = {
        "environmental": {"temperature": 27.5, "motion": True, "valid": True},
        "temporal": {"hour": 10},
        "runtime": {"active_model_version": 2, "model_confidence": 0.8},
    }
    activity = {"activity": "Working", "confidence": 0.85}
    profile = {
        "preferences": {
            "preferred_temperature": {"current_value": 21.0, "confidence": 0.90}
        }
    }
    
    # Mock policies
    policy_comfort = MagicMock(identifier="comfort_policy", priority=4)
    policy_sec = MagicMock(identifier="security_policy", priority=6)
    
    candidates = [
        {"action": "actuate_relay", "policy": "comfort_policy", "reason": "COMFORT_COOLING", "confidence": 0.8, "priority": 4},
        {"action": "no_action", "policy": "security_policy", "reason": "SECURITY_SAFE", "confidence": 0.9, "priority": 6},
    ]

    device_registry = AsyncMock()
    device_registry.get_all_devices = AsyncMock(return_value=[
        {"id": "device_1", "reliability": 0.95, "health": "healthy"}
    ])

    decision = await engine.reason(
        context=context,
        activity=activity,
        profile=profile,
        policies=[policy_comfort, policy_sec],
        candidate_decisions=candidates,
        model_output={"presence_prob": 0.9, "anomaly_score": 0.1},
        device_registry=device_registry,
    )

    assert decision["decision_id"] is not None
    assert decision["selected_policy"] == "security_policy"  # Priority 6 wins over 4
    assert decision["requested_action"] == "no_action"
    assert len(decision["alternative_actions"]) == 2
    assert len(decision["evidence_list"]) > 0


# ── Explainability Engine Tests ───────────────────────────────────────────────

def test_explainability_engine_formatting() -> None:
    engine = ExplainabilityEngine()

    decision = {
        "decision_id": "test-uuid",
        "selected_policy": "user_override_policy",
        "requested_action": "actuate_relay",
        "reason": "USER_OVERRIDE_TRIGGERED",
        "confidence": 0.95,
        "evidence_list": [{"description": "User requested override"}],
        "alternative_actions": [
            {"action": "actuate_relay", "score": 0.95, "policy": "user_override_policy", "reason": "USER_OVERRIDE_TRIGGERED"},
            {"action": "no_action", "score": 0.40, "policy": "background_policy", "reason": "NOMINAL_BACKGROUND_FALLBACK"}
        ]
    }

    context = {
        "environmental": {"temperature": 22.0, "valid": True},
        "temporal": {"hour": 8},
        "runtime": {"model_confidence": 0.9},
    }
    activity = {"activity": "Working", "confidence": 0.90}
    profile = {
        "preferences": {
            "preferred_temperature": {"confidence": 0.85}
        }
    }

    explanation = engine.explain(decision, context, activity, profile)

    assert explanation.selected_policy == "user_override_policy"
    assert "MANUAL_OVERRIDE" in explanation.reason_codes
    assert "TIME_BASED" in explanation.reason_codes
    assert explanation.confidence_summary.overall_confidence == 0.95
    assert explanation.confidence_summary.context_confidence == 1.0
    assert explanation.confidence_summary.activity_confidence == 0.90
    assert explanation.confidence_summary.policy_confidence == 0.85


# ── Cognitive Memory Tests ───────────────────────────────────────────────────

def test_cognitive_memory_retention_and_gc() -> None:
    memory = CognitiveMemory(max_entries=3, max_age_days=1)
    
    # Store items
    memory.store_memory("decision", {"id": "d1", "val": 10})
    memory.store_memory("decision", {"id": "d2", "val": 20})
    memory.store_memory("decision", {"id": "d3", "val": 30})
    memory.store_memory("decision", {"id": "d4", "val": 40})  # triggers capacity GC

    stats = memory.get_statistics()
    assert stats["decision"] == 3  # clamped to max_entries=3
    
    # Retrieve
    res = memory.query_memories("decision", {"id": "d3"})
    assert len(res) == 1
    assert res[0]["val"] == 30

    # Retrieve missing
    res_missing = memory.query_memories("decision", {"id": "d1"})
    assert len(res_missing) == 0  # pruned by GC


# ── Device Registry Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_device_registry_health_and_capabilities() -> None:
    graph = AsyncMock()
    graph._graph = MagicMock()
    
    registry = DeviceRegistry(graph=graph, ws_bus=None)
    
    # Register device
    await registry.register_device("sentinel_01", "sentinel", {"firmware_version": "2.0.1"})
    assert graph.upsert_node.called
    
    node_args = graph.upsert_node.call_args[1]
    assert node_args["device_type"] == "sentinel"
    assert "climate" in node_args["capabilities"]
    
    # Mock graph search for check_capability
    graph._graph.__contains__ = MagicMock(return_value=True)
    graph._graph.nodes = {"sentinel_01": {"capabilities": ["climate", "sensors"]}}
    
    has_climate = await registry.check_capability("sentinel_01", "climate")
    has_lighting = await registry.check_capability("sentinel_01", "lighting")
    
    assert has_climate is True
    assert has_lighting is False


# ── Cognitive API REST Endpoint Tests ─────────────────────────────────────────

def test_cognitive_api_endpoints() -> None:
    # Set up mocks
    memory = MagicMock()
    graph = MagicMock()
    ws_bus = MagicMock()
    serial_bridge = MagicMock()
    serial_writer = MagicMock()
    identity_manager = MagicMock()
    deployment_service = MagicMock()
    sensor_processor = MagicMock()
    event_processor = MagicMock()
    metrics = MagicMock()
    model_manager = MagicMock()
    learning_loop = MagicMock()
    device_registry = AsyncMock()
    
    # Mock Policy Engine
    policy = MagicMock()
    policy._latest_decision = {
        "decision_id": "test-uuid-99",
        "selected_policy": "comfort_policy",
        "requested_action": "actuate_relay",
        "reason": "temp_warm",
        "confidence": 0.85,
        "explanation": {
            "decision_summary": "Adjusted climate",
            "reason_codes": ["USER_PREFERENCE"]
        }
    }
    policy.policy_pipeline._decision_history = [policy._latest_decision]
    policy.cognitive_memory.get_statistics = MagicMock(return_value={"decision": 5, "preference": 2})
    policy.device_registry.get_all_devices = AsyncMock(return_value=[
        {"id": "device_1", "device_type": "sentinel", "health": "healthy", "reliability": 0.99, "average_response_time_ms": 12.0}
    ])
    policy.knowledge_base.get_summary = AsyncMock(return_value={"status": "all_nominal"})

    app = create_app(
        memory=memory,
        graph=graph,
        ws_bus=ws_bus,
        policy=policy,
        metrics=metrics,
        sensor_processor=sensor_processor,
        event_processor=event_processor,
        model_manager=model_manager,
        learning_loop=learning_loop,
        serial_bridge=serial_bridge,
        serial_writer=serial_writer,
        identity_manager=identity_manager,
        device_registry=device_registry,
        voice_manager=MagicMock(),
        deployment_service=deployment_service,
    )

    client = TestClient(app)

    # 1. Latest Decision Endpoint
    resp = client.get("/api/v1/cognitive/decision/latest")
    assert resp.status_code == 200
    assert resp.json()["decision"]["decision_id"] == "test-uuid-99"

    # 2. Decision History Endpoint
    resp = client.get("/api/v1/cognitive/decision/history")
    assert resp.status_code == 200
    assert len(resp.json()["history"]) == 1

    # 3. Decision Explanation Endpoint
    resp = client.get("/api/v1/cognitive/explanation/test-uuid-99")
    assert resp.status_code == 200
    assert resp.json()["explanation"]["decision_summary"] == "Adjusted climate"

    # 4. Memory Stats Endpoint
    resp = client.get("/api/v1/cognitive/memory/stats")
    assert resp.status_code == 200
    assert resp.json()["statistics"]["decision"] == 5

    # 5. Devices Reliability Endpoint
    resp = client.get("/api/v1/cognitive/devices/reliability")
    assert resp.status_code == 200
    assert resp.json()["devices"][0]["reliability"] == 0.99

    # 6. Knowledge Summary Endpoint
    resp = client.get("/api/v1/cognitive/knowledge/summary")
    assert resp.status_code == 200
    assert resp.json()["knowledge_summary"]["status"] == "all_nominal"
