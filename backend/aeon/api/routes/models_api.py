"""
GET  /api/v1/models/active          — current active model + metadata
GET  /api/v1/models/inventory       — all installed models with status
GET  /api/v1/models/deployment/status  — current deployment state
GET  /api/v1/models/deployment/history — last N deployments
GET  /api/v1/models/statistics      — runtime statistics
GET  /api/v1/models/score           — current composite model score
POST /api/v1/models/rollback        — trigger rollback to previous model
POST /api/v1/models/statistics/record — firmware reports an inference result
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from shared.types.deployment import RollbackReason
from shared.errors.model_errors import DeploymentError, RollbackError

log = structlog.get_logger(__name__)
router = APIRouter(tags=["models"])


# ── Request / Response models ─────────────────────────────────────────────────

class RollbackRequest(BaseModel):
    reason: str = "manual_rollback"


class InferenceRecordRequest(BaseModel):
    confidence: float
    latency_ms: float
    success:    bool = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/models/active")
async def active_model(request: Request):
    """Return metadata for the currently active (committed) model."""
    manager = request.app.state.model_manager
    if manager.active_model is None:
        raise HTTPException(status_code=404, detail="No active model")
    return {"active_model": manager.active_model.to_dict()}


@router.get("/models/inventory")
async def model_inventory(request: Request):
    """Return all known model entries and their activation state."""
    manager = request.app.state.model_manager
    return {
        "inventory": manager.get_inventory(),
        "installed": manager.list_models(),
    }


@router.get("/models/deployment/status")
async def deployment_status(request: Request):
    """Return the current deployment lifecycle state."""
    manager = request.app.state.model_manager
    return manager.get_deployment_status()


@router.get("/models/deployment/history")
async def deployment_history(request: Request, limit: int = 10):
    """Return the last N deployment records."""
    manager = request.app.state.model_manager
    return {"history": manager.get_deployment_history(limit=max(1, min(limit, 100)))}


@router.get("/models/statistics")
async def runtime_statistics(request: Request):
    """Return live runtime inference statistics."""
    manager = request.app.state.model_manager
    return {"statistics": manager.runtime_statistics.to_dict()}


@router.get("/models/score")
async def model_score(request: Request):
    """Return the latest composite model quality score."""
    manager = request.app.state.model_manager
    if manager._current_score is None:
        return {"score": None, "note": "No score computed yet"}
    return {"score": manager._current_score.to_dict()}


@router.post("/models/rollback")
async def trigger_rollback(body: RollbackRequest, request: Request):
    """
    Trigger a rollback to the previous model.
    Requires a DeploymentService bound on app.state.deployment_service.
    """
    svc = getattr(request.app.state, "deployment_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="DeploymentService not available")

    try:
        reason = RollbackReason(body.reason)
    except ValueError:
        reason = RollbackReason.MANUAL_ROLLBACK

    try:
        result = await svc.rollback(reason)
    except DeploymentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return result


@router.post("/models/statistics/record")
async def record_inference_result(body: InferenceRecordRequest, request: Request):
    """
    Called by the firmware bridge or integration tests to report inference results.
    Updates live statistics in ModelManager.
    """
    manager = request.app.state.model_manager
    manager.record_inference(
        confidence = body.confidence,
        latency_ms = body.latency_ms,
        success    = body.success,
    )
    return {"ok": True, "stats": manager.runtime_statistics.to_dict()}
