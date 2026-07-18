"""
GET /api/v1/learning/status
POST /api/v1/learning/trigger
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["learning"])

@router.get("/learning/status")
async def learning_status(request: Request):
    learning = request.app.state.learning_loop
    return {
        "last_train": learning._last_train.isoformat() if learning._last_train else None,
        "is_dreaming": learning._dream._is_dreaming,
        "versions": learning._versioning._registry
    }

@router.post("/learning/trigger")
async def trigger_learning(request: Request):
    learning = request.app.state.learning_loop
    await learning.trigger_online_learning()
    return {"ok": True, "status": "online_learning_triggered"}

@router.post("/learning/dream")
async def trigger_dream(request: Request):
    learning = request.app.state.learning_loop
    await learning.trigger_dream_state()
    return {"ok": True, "status": "dream_state_triggered"}
