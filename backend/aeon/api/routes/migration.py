"""
POST /api/v1/migration/export/{user_id}   — export identity for portability
POST /api/v1/migration/import             — import identity on new device
"""
from __future__ import annotations

import json
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["migration"])


@router.get("/migration/export/{user_id}")
async def export_identity(user_id: str, request: Request):
    """
    Export the user's knowledge-graph subgraph as a portable JSON blob.
    The blob can be imported on any ÆON device to migrate identity.
    """
    graph = request.app.state.graph
    profile = await graph.export_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, "profile": profile}


class ImportRequest(BaseModel):
    profile: dict


@router.post("/migration/import")
async def import_identity(body: ImportRequest, request: Request):
    """
    Import a previously exported identity profile.
    Merges the incoming graph nodes into the local knowledge graph.
    """
    graph = request.app.state.graph
    await graph.import_profile(body.profile)
    return {"ok": True, "nodes_imported": len(body.profile.get("nodes", []))}
