"""
aeon/api/routes/digital_twin.py

REST endpoints for the Digital Twin engine.

GET  /api/v1/twin/state        — full twin state (all appliances + context)
POST /api/v1/twin/ac/mode      — override AC mode
POST /api/v1/twin/light/scene  — set light scene
POST /api/v1/twin/vacuum/start — start vacuum cleaning run
POST /api/v1/twin/vacuum/dock  — send vacuum home
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["digital_twin"])


def _twin_manager(request: Request):
    """Return the TwinManager from app state (injected at startup)."""
    return getattr(request.app.state, "twin_manager", None)


@router.get("/twin/state")
async def twin_state(request: Request):
    """Return the current state of all digital twins and the room context."""
    mgr = _twin_manager(request)
    if mgr is None:
        return {"error": "Digital twin engine not initialised"}
    return mgr.snapshot()


class ACModeBody(BaseModel):
    mode: str   # "off" | "cool" | "eco" | "quiet"


@router.post("/twin/ac/mode")
async def set_ac_mode(body: ACModeBody, request: Request):
    mgr = _twin_manager(request)
    if mgr is None:
        return {"ok": False, "error": "Twin engine not initialised"}
    mgr.ac._set_mode(body.mode)
    await mgr._publish()
    return {"ok": True, "mode": body.mode}


class LightSceneBody(BaseModel):
    scene: str  # "auto" | "movie" | "work" | "sleep" | "away"


@router.post("/twin/light/scene")
async def set_light_scene(body: LightSceneBody, request: Request):
    mgr = _twin_manager(request)
    if mgr is None:
        return {"ok": False, "error": "Twin engine not initialised"}
    mgr.light.set_scene(body.scene)
    await mgr._publish()
    return {"ok": True, "scene": body.scene}


@router.post("/twin/vacuum/start")
async def start_vacuum(request: Request):
    mgr = _twin_manager(request)
    if mgr is None:
        return {"ok": False, "error": "Twin engine not initialised"}
    mgr.vacuum._start_cleaning()
    await mgr._publish()
    return {"ok": True, "state": "cleaning"}


@router.post("/twin/vacuum/dock")
async def dock_vacuum(request: Request):
    mgr = _twin_manager(request)
    if mgr is None:
        return {"ok": False, "error": "Twin engine not initialised"}
    mgr.vacuum.state = "returning"
    await mgr._publish()
    return {"ok": True, "state": "returning"}
