"""
aeon/models/manager.py — Model lifecycle and registry manager.

Wraps QNNManager to provide model status, version tracking, and hot-reloading.
Delegates to QNNManager.get_status() so the WebSocket bus has a single
authoritative source for backend, active_models, and metrics.
"""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    from aeon_platform.runtime.qnn.manager import QNNManager

log = structlog.get_logger(__name__)


class ModelManager:
    def __init__(self, qnn: "QNNManager", model_dir: Path) -> None:
        self._qnn      = qnn
        self._model_dir = model_dir

    def get_status(self) -> dict[str, Any]:
        """
        Return the full QNN status dict.

        Keys returned (used by WebSocket bus and system route):
          backend        — "QNN_HTP" | "ONNX" | "UNAVAILABLE"
          active_models  — list[str]
          metadata       — dict
          metrics        — {model_name: {mean, p50, p95, p99}}
        """
        return self._qnn.get_status()

    def list_models(self) -> list[dict[str, Any]]:
        """List all loaded models with file metadata."""
        status  = self._qnn.get_status()
        models  = []
        for name in status.get("active_models", []):
            bin_path  = self._model_dir / f"{name}.bin"
            onnx_path = self._model_dir / f"{name}.onnx"

            size = 0
            fmt  = "unknown"
            if bin_path.exists():
                size = bin_path.stat().st_size
                fmt  = "QNN (.bin)"
            elif onnx_path.exists():
                size = onnx_path.stat().st_size
                fmt  = "ONNX (.onnx)"

            meta = status.get("metadata", {}).get(name, {})
            models.append({
                "name":        name,
                "format":      fmt,
                "size_bytes":  size,
                "status":      "loaded",
                "loaded_at":   meta.get("loaded_at"),
            })
        return models

    async def reload_model(self, name: str) -> bool:
        """Hot-reload a model from disk (e.g., after learning updates)."""
        log.info("model_manager.reload", name=name)
        return await self._qnn.reload_model(name)
