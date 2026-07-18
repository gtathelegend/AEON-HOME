"""
aeon/qnn/scheduler.py — Inference Scheduler.

Executes synchronous QNN/ONNX inferences in a thread pool to avoid blocking
the main asyncio event loop.
"""

from __future__ import annotations

import asyncio
import structlog
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

log = structlog.get_logger(__name__)


class InferenceScheduler:
    """Schedules inferences asynchronously."""

    def __init__(self, max_workers: int = 4) -> None:
        # NPU operations are fast, but blocking. A thread pool lets us queue
        # concurrent requests (e.g. vision vs telemetry) without starving the app.
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="qnn_worker"
        )

    async def schedule(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run a synchronous inference function in the thread pool."""
        loop = asyncio.get_running_loop()
        
        # functools.partial is needed if kwargs are passed
        from functools import partial
        if kwargs:
            pfunc = partial(func, *args, **kwargs)
            return await loop.run_in_executor(self._executor, pfunc)
        else:
            return await loop.run_in_executor(self._executor, func, *args)
            
    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
