"""
aeon/qnn/manager.py — QNN Runtime Manager orchestrator.

Coordinates the loader, session manager, scheduler, tensor processor, and 
performance monitor to provide a unified, asynchronous AI execution engine.
"""

from __future__ import annotations

import structlog
import time
from pathlib import Path
from typing import Any

import numpy as np

from platform.runtime.qnn.loader import ModelLoader
from platform.runtime.qnn.session import SessionManager
from platform.runtime.qnn.scheduler import InferenceScheduler
from platform.runtime.qnn.tensor import TensorProcessor
from platform.runtime.qnn.metrics import PerformanceMonitor

log = structlog.get_logger(__name__)

# Try to import QNN to check if we are using the NPU wrapper
try:
    import qnn  # type: ignore[import]
    _QNN_AVAILABLE = True
except ImportError:
    _QNN_AVAILABLE = False


class QNNManager:
    """Orchestrates QNN/ONNX inference pipelines."""

    def __init__(self, model_dir: Path | str, use_npu: bool = True) -> None:
        self._model_dir = Path(model_dir)
        self._use_npu = use_npu and _QNN_AVAILABLE
        
        self._loader = ModelLoader(self._model_dir, use_npu)
        self._sessions = SessionManager(use_npu)
        self._scheduler = InferenceScheduler(max_workers=4)
        self._tensor = TensorProcessor()
        self._metrics = PerformanceMonitor()
        
        # Track loaded model metadata
        self._metadata: dict[str, dict[str, Any]] = {}

    async def init(self) -> None:
        """Load all standard models asynchronously during startup."""
        model_names = [
            "presence_classifier",
            "anomaly_detector",
            "occupancy_predictor",
        ]
        
        # Loading models can be slow (especially NPU graph loading), run in thread pool
        for name in model_names:
            await self._scheduler.schedule(self._load_and_register_sync, name)
            
        log.info("qnn_manager.init_complete", 
                 backend="QNN" if self._use_npu else "ONNX",
                 active_models=self._sessions.active_models)

    def _load_and_register_sync(self, name: str) -> None:
        """Synchronous part of model loading (runs in thread pool)."""
        session, fmt = self._loader.load(name)
        if session:
            self._sessions.add_session(name, session)
            self._metadata[name] = {"format": fmt, "loaded_at": time.time()}

    async def reload_model(self, name: str) -> bool:
        """Hot-reload a model (e.g. after continuous learning)."""
        log.info("qnn_manager.hot_reload_start", name=name)
        # Offload file loading to thread pool
        success = await self._scheduler.schedule(self._reload_sync, name)
        if success:
            log.info("qnn_manager.hot_reload_complete", name=name)
        return success
        
    def _reload_sync(self, name: str) -> bool:
        """Synchronous reload routine."""
        session, fmt = self._loader.load(name)
        if not session:
            log.error("qnn_manager.hot_reload_failed", name=name)
            return False
            
        # The add_session call handles locking
        self._sessions.add_session(name, session)
        self._metadata[name] = {"format": fmt, "loaded_at": time.time()}
        return True

    def _execute_sync(self, name: str, processed_inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Synchronous execution wrapper that runs under a per-model lock."""
        lock = self._sessions.get_lock(name)
        with lock:
            session = self._sessions.get_session(name)
            if not session:
                raise RuntimeError(f"Model '{name}' not loaded.")
                
            start_t = time.perf_counter()
            
            # Execute based on backend
            if self._use_npu and _QNN_AVAILABLE and isinstance(session, qnn.ModelContext): # type: ignore
                outputs = session.execute(processed_inputs)
            else:
                # ONNX
                outputs_list = session.run(None, processed_inputs)
                out_names = [o.name for o in session.get_outputs()]
                outputs = dict(zip(out_names, outputs_list))
                
            latency_ms = (time.perf_counter() - start_t) * 1000
            
        return outputs, latency_ms

    async def infer(self, model_name: str, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """
        Run an asynchronous inference pipeline.
        
        1. Preprocess inputs
        2. Schedule execution on a worker thread
        3. Postprocess outputs
        4. Track metrics
        """
        # 1. Preprocess (fast, run on main thread)
        feed = self._tensor.preprocess(model_name, inputs)
        
        # 2. Execute (slow/blocking, run on scheduler)
        outputs, latency_ms = await self._scheduler.schedule(self._execute_sync, model_name, feed)
        
        # 3. Track metrics
        self._metrics.record_latency(model_name, latency_ms)
        
        # 4. Postprocess
        return self._tensor.postprocess(model_name, outputs)

    async def benchmark(self, model_name: str, iterations: int = 100) -> dict[str, float]:
        """Run a benchmark loop for a model and return stats."""
        # Use dummy inputs of correct shape
        # In a real implementation we would interrogate the model for shapes
        # Here we just use a standard 1x7 feature vector
        dummy_input = {"input": np.zeros((1, 7), dtype=np.float32)}
        
        for _ in range(iterations):
            await self.infer(model_name, dummy_input)
            
        return self._metrics.get_stats(model_name)

    def get_status(self) -> dict[str, Any]:
        """Expose current state to the API."""
        if self._use_npu and _QNN_AVAILABLE:
            backend_str = "QNN_HTP"
        elif self._sessions.active_models:
            backend_str = "ONNX"
        else:
            backend_str = "UNAVAILABLE"

        return {
            "backend": backend_str,
            "active_models": self._sessions.active_models,
            "metadata": self._metadata,
            "metrics": self._metrics.get_all_stats(),
        }
        
    def shutdown(self) -> None:
        self._scheduler.shutdown()
