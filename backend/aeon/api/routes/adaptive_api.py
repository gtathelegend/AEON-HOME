# backend/aeon/api/routes/adaptive_api.py

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Dict

log = structlog.get_logger(__name__)
router = APIRouter(tags=["adaptive"])


class PreferenceUpdateRequest(BaseModel):
    setting: str
    value: Any
    source: str = "api_update"


@router.get("/adaptive/context")
async def get_current_context(request: Request):
    """Retrieve the unified environmental, behavioral, and temporal context."""
    policy = request.app.state.policy
    if not hasattr(policy, "context_engine"):
        raise HTTPException(status_code=503, detail="Context engine not initialized")
    ctx = await policy.context_engine.get_current_context()
    return {"context": ctx}


@router.get("/adaptive/activity")
async def get_current_activity(request: Request):
    """Retrieve the rolling activity history and current activity."""
    policy = request.app.state.policy
    if not hasattr(policy, "activity_engine"):
        raise HTTPException(status_code=503, detail="Activity engine not initialized")
    history = policy.activity_engine.get_history()
    current = policy.activity_engine._current_activity
    return {"current": current, "history": history}


@router.get("/adaptive/profile")
async def get_user_profile(request: Request, user_id: str = "default_user"):
    """Retrieve the active user profile with adaptive preferences."""
    policy = request.app.state.policy
    if not hasattr(policy, "profile_engine"):
        raise HTTPException(status_code=503, detail="Profile engine not initialized")
    profile = await policy.profile_engine.get_profile(user_id)
    return {"profile": profile}


@router.get("/adaptive/decision")
async def get_decision_history(request: Request):
    """Retrieve the policy engine's decision log."""
    policy = request.app.state.policy
    if not hasattr(policy, "policy_pipeline"):
        raise HTTPException(status_code=503, detail="Policy pipeline not initialized")
    history = policy.policy_pipeline._decision_history
    return {"history": history}


@router.get("/adaptive/policies")
async def get_policies_metadata(request: Request):
    """Retrieve metadata and configurations for all registered policies."""
    policy = request.app.state.policy
    if not hasattr(policy, "policy_pipeline"):
        raise HTTPException(status_code=503, detail="Policy pipeline not initialized")
    policies = []
    for p in policy.policy_pipeline._policies:
        policies.append({
            "identifier": p.identifier,
            "priority": p.priority,
            "enabled": getattr(p, "enabled", True),
            "history_size": len(getattr(p, "_history", [])),
        })
    return {"policies": policies}


@router.post("/adaptive/preference")
async def update_user_preference(body: PreferenceUpdateRequest, request: Request, user_id: str = "default_user"):
    """Update or record a preference learning signal via API."""
    policy = request.app.state.policy
    if not hasattr(policy, "profile_engine"):
        raise HTTPException(status_code=503, detail="Profile engine not initialized")
    await policy.profile_engine.record_signal(
        user_id=user_id,
        setting=body.setting,
        value=body.value,
        source=body.source,
    )
    return {"ok": True}
