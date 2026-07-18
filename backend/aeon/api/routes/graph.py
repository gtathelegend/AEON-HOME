"""
GET  /api/v1/graph/nodes               — list all nodes (optional ?type=filter)
GET  /api/v1/graph/edges               — list all edges (optional ?rel=filter)
POST /api/v1/graph/nodes               — create arbitrary node
POST /api/v1/graph/edges               — create arbitrary edge
GET  /api/v1/graph/visualize           — export Cytoscape JSON
GET  /api/v1/graph/search              — find shortest path between ?src=...&dst=...
GET  /api/v1/graph/reason/{user_id}    — infer context for a user
GET  /api/v1/graph/profile/{user_id}   — export user subgraph
POST /api/v1/graph/preferences/{user_id} — update a preference
"""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

router = APIRouter(tags=["graph"])


class PreferenceUpdate(BaseModel):
    setting: str
    value:   Any

class NodeCreate(BaseModel):
    node_id: str
    attrs: dict[str, Any]

class EdgeCreate(BaseModel):
    src: str
    dst: str
    rel: str
    attrs: dict[str, Any]


@router.get("/graph/nodes")
async def get_nodes(request: Request, type: Optional[str] = None):
    graph = request.app.state.graph
    async with graph._lock:
        nodes = []
        for n, d in graph._graph.nodes(data=True):
            if type and d.get("type") != type:
                continue
            nodes.append({"id": n, **d})
        return {"nodes": nodes}

@router.get("/graph/edges")
async def get_edges(request: Request, rel: Optional[str] = None):
    graph = request.app.state.graph
    async with graph._lock:
        edges = []
        for u, v, d in graph._graph.edges(data=True):
            if rel and d.get("rel") != rel:
                continue
            edges.append({"src": u, "dst": v, **d})
        return {"edges": edges}

@router.post("/graph/nodes")
async def create_node(body: NodeCreate, request: Request):
    graph = request.app.state.graph
    await graph.upsert_node(body.node_id, **body.attrs)
    return {"ok": True, "node_id": body.node_id}

@router.post("/graph/edges")
async def create_edge(body: EdgeCreate, request: Request):
    graph = request.app.state.graph
    await graph.upsert_edge(body.src, body.dst, body.rel, **body.attrs)
    return {"ok": True, "src": body.src, "dst": body.dst, "rel": body.rel}

@router.get("/graph/visualize")
async def visualize_graph(request: Request):
    graph = request.app.state.graph
    return await graph.export_cytoscape()

@router.get("/graph/search")
async def search_graph(request: Request, src: str, dst: str):
    graph = request.app.state.graph
    path = await graph.find_shortest_path(src, dst)
    if not path:
        raise HTTPException(status_code=404, detail="No path found")
    return {"path": path}

@router.get("/graph/reason/{user_id}")
async def reason_context(user_id: str, request: Request):
    graph = request.app.state.graph
    context = await graph.infer_context(user_id)
    return context

@router.get("/graph/profile/{user_id}")
async def export_profile(user_id: str, request: Request):
    graph = request.app.state.graph
    profile = await graph.export_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found in graph")
    return profile

@router.post("/graph/preferences/{user_id}")
async def update_preference(
    user_id: str, body: PreferenceUpdate, request: Request
):
    graph = request.app.state.graph
    await graph.update_preference(user_id, body.setting, body.value)
    return {"ok": True, "user_id": user_id,
            "setting": body.setting, "value": body.value}
