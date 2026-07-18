"""
GET  /api/v1/decisions        — list recent policy decisions
POST /api/v1/decisions/{id}/label — submit user feedback (false alarm / correct)
"""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["decisions"])


class LabelRequest(BaseModel):
    label: int   # 1 = correct, 0 = false alarm


@router.get("/decisions")
async def list_decisions(request: Request, limit: int = 50):
    memory = request.app.state.memory
    async with memory._db.execute(
        "SELECT id,ts,action,confidence,reason,label FROM decisions "
        "ORDER BY id DESC LIMIT ?", (limit,)
    ) as cur:
        rows = await cur.fetchall()
    return [
        {"id": r[0], "ts": r[1], "action": r[2],
         "confidence": r[3], "reason": r[4], "label": r[5]}
        for r in rows
    ]


@router.post("/decisions/{decision_id}/label")
async def label_decision(
    decision_id: int, body: LabelRequest, request: Request
):
    if body.label not in (0, 1):
        raise HTTPException(status_code=422, detail="label must be 0 or 1")
    memory = request.app.state.memory
    await memory.label_decision(decision_id, body.label)
    return {"ok": True, "id": decision_id, "label": body.label}
