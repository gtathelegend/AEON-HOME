# backend/aeon/api/routes/cognitive_api.py

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request
from typing import Any, Dict

log = structlog.get_logger(__name__)
router = APIRouter(tags=["cognitive"])


@router.get("/cognitive/decision/latest")
async def get_latest_decision(request: Request):
    """Retrieve the latest reasoning decision trace."""
    policy = request.app.state.policy
    if not hasattr(policy, "_latest_decision") or not policy._latest_decision:
        return {"decision": None}
    return {"decision": policy._latest_decision}


@router.get("/cognitive/decision/history")
async def get_decision_history(request: Request):
    """Retrieve the rolling list of all decisions."""
    policy = request.app.state.policy
    if not hasattr(policy, "policy_pipeline") or not policy.policy_pipeline:
        raise HTTPException(status_code=503, detail="Policy pipeline not initialized")
    history = policy.policy_pipeline._decision_history
    return {"history": history}


@router.get("/cognitive/explanation/{decision_id}")
async def get_decision_explanation(decision_id: str, request: Request):
    """Retrieve the structured explanation for a specific decision ID."""
    policy = request.app.state.policy
    if not hasattr(policy, "policy_pipeline") or not policy.policy_pipeline:
        raise HTTPException(status_code=503, detail="Policy pipeline not initialized")
    
    # Search history for decision
    found_dec = None
    for dec in policy.policy_pipeline._decision_history:
        if dec.get("decision_id") == decision_id:
            found_dec = dec
            break
            
    if not found_dec:
        raise HTTPException(status_code=404, detail="Decision ID not found in history")
        
    return {"explanation": found_dec.get("explanation", {})}


@router.get("/cognitive/memory/stats")
async def get_memory_stats(request: Request):
    """Retrieve count statistics for all cognitive memory categories."""
    policy = request.app.state.policy
    if not hasattr(policy, "cognitive_memory") or not policy.cognitive_memory:
        raise HTTPException(status_code=503, detail="Cognitive memory not initialized")
    stats = policy.cognitive_memory.get_statistics()
    return {"statistics": stats}


@router.get("/cognitive/devices/reliability")
async def get_device_reliability(request: Request):
    """Retrieve health status and reliability metrics for all connected devices."""
    policy = request.app.state.policy
    if not hasattr(policy, "device_registry") or not policy.device_registry:
        raise HTTPException(status_code=503, detail="Device registry not initialized")
    devices = await policy.device_registry.get_all_devices()
    
    reliability_report = []
    for d in devices:
        reliability_report.append({
            "device_id": d.get("id"),
            "device_type": d.get("device_type"),
            "health": d.get("health", "healthy"),
            "reliability": d.get("reliability", 1.0),
            "average_response_time_ms": d.get("average_response_time_ms", 15.0),
            "error_count": d.get("error_count", 0),
            "success_count": d.get("success_count", 0),
        })
    return {"devices": reliability_report}


@router.get("/cognitive/knowledge/summary")
async def get_knowledge_summary(request: Request):
    """Retrieve summary representation of the runtime knowledge base."""
    policy = request.app.state.policy
    if not hasattr(policy, "knowledge_base") or not policy.knowledge_base:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")
    summary = await policy.knowledge_base.get_summary()
    return {"knowledge_summary": summary}
