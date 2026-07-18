"""
aeon/qnn/loader.py — Model Loader.

Discovers and loads .bin (QNN) or .onnx (Fallback) models.
"""

from __future__ import annotations

import structlog
from pathlib import Path
from typing import Any

# QNN is optional
try:
    import qnn  # type: ignore[import]
    _QNN_AVAILABLE = True
except ImportError:
    _QNN_AVAILABLE = False
    import onnxruntime as ort  # type: ignore[import]

log = structlog.get_logger(__name__)


class ModelLoader:
    """Discovers and loads QNN/ONNX models from disk."""

    def __init__(self, model_dir: Path, use_npu: bool) -> None:
        self._model_dir = Path(model_dir)
        self._use_npu = use_npu and _QNN_AVAILABLE

    def load(self, name: str) -> tuple[Any, str]:
        """
        Attempt to load a model by name.
        Returns the session object and the format ("QNN" or "ONNX"), or (None, "")
        """
        if self._use_npu:
            path = self._model_dir / f"{name}.bin"
            if path.exists():
                log.info("qnn_loader.loading_npu", path=str(path))
                ctx = qnn.ModelContext(str(path), backend=qnn.Backend.HTP)
                ctx.load()
                return ctx, "QNN"
            log.warning("qnn_loader.npu_model_missing", path=str(path))

        # Fallback to ONNX
        path = self._model_dir / f"{name}.onnx"
        if path.exists():
            log.info("qnn_loader.loading_cpu", path=str(path))
            import onnxruntime as ort
            session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            return session, "ONNX"

        log.error("qnn_loader.not_found", name=name)
        return None, ""
