"""GET /api/v1/health — liveness + readiness probe."""
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status:    str
    version:   str
    timestamp: str
    uptime_ok: bool


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        uptime_ok=True,
    )
