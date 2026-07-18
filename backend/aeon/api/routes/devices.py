"""GET /api/v1/devices — connected device registry."""
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["devices"])


class DeviceInfo(BaseModel):
    id:     str
    type:   str
    status: str
    meta:   dict


@router.get("/devices", response_model=list[DeviceInfo])
async def list_devices(request: Request) -> list[DeviceInfo]:
    # In production these come from the knowledge graph.
    # Returning static topology for now — the graph module populates this
    # as devices announce themselves via the serial protocol.
    graph = request.app.state.graph
    nodes = [
        (n, d) for n, d in graph._graph.nodes(data=True)
        if d.get("type") == "device"
    ]
    return [
        DeviceInfo(
            id=n,
            type=d.get("device_type", "unknown"),
            status=d.get("status", "unknown"),
            meta={k: v for k, v in d.items()
                  if k not in ("type", "device_type", "status")},
        )
        for n, d in nodes
    ]
