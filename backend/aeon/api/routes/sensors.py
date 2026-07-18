"""
GET /api/v1/sensors/latest
GET /api/v1/sensors/history
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["sensors"])

@router.get("/sensors/latest")
async def latest_sensors(request: Request):
    processor = request.app.state.sensor_processor
    data = processor.get_latest()
    return data if data else {}

@router.get("/sensors/history")
async def sensor_history(request: Request, minutes: int = 60):
    processor = request.app.state.sensor_processor
    data = await processor.get_history(minutes)
    return data
