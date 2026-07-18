"""
GET /api/v1/events
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["events"])

@router.get("/events")
async def get_events(request: Request, limit: int = 50):
    processor = request.app.state.event_processor
    data = await processor.get_recent_events(limit)
    return data
