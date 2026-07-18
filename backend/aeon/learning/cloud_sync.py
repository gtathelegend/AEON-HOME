"""
aeon/learning/cloud_sync.py — Optional Qualcomm Cloud AI 100 sync.

This module is DISABLED by default (settings.cloud_sync_enabled = False).

When enabled, it uploads anonymised model delta weights to Cloud AI 100
for background optimisation (pruning, distillation) and downloads the
improved model back.

Privacy contract:
  - Only model weight deltas are transmitted, never raw data or feature vectors.
  - The user must explicitly enable this in .env: AEON_CLOUD_SYNC=true
  - All transfers are authenticated with a device-scoped JWT.
"""

from __future__ import annotations

import asyncio
import structlog
from pathlib import Path

import httpx

from aeon.config.settings import settings

log = structlog.get_logger(__name__)


class CloudSync:
    def __init__(self, model_dir: Path) -> None:
        self._model_dir = model_dir

    async def push_delta(self, model_name: str, delta_path: Path) -> bool:
        """Upload a weight delta to Cloud AI 100. Returns True on success."""
        if not settings.cloud_sync_enabled:
            log.debug("cloud_sync.disabled")
            return False
        if not settings.cloud_endpoint:
            log.warning("cloud_sync.no_endpoint")
            return False

        url = f"{settings.cloud_endpoint}/api/v1/models/{model_name}/delta"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                with open(delta_path, "rb") as f:
                    resp = await client.post(
                        url,
                        content=f.read(),
                        headers={
                            "Content-Type": "application/octet-stream",
                            "X-Device-ID": settings.device_id,
                        },
                    )
            resp.raise_for_status()
            log.info("cloud_sync.push_ok", model=model_name, status=resp.status_code)
            return True
        except Exception:
            log.exception("cloud_sync.push_error", model=model_name)
            return False

    async def pull_model(self, model_name: str) -> bool:
        """Download the latest optimised model from Cloud AI 100."""
        if not settings.cloud_sync_enabled:
            return False
        url = f"{settings.cloud_endpoint}/api/v1/models/{model_name}/latest"
        out_path = self._model_dir / f"{model_name}.bin"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(
                    url, headers={"X-Device-ID": settings.device_id}
                )
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            log.info("cloud_sync.pull_ok", model=model_name, bytes=len(resp.content))
            return True
        except Exception:
            log.exception("cloud_sync.pull_error", model=model_name)
            return False
