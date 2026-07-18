"""
aeon/qnn/metrics.py — Performance monitoring for QNN inference.

Tracks latency percentiles and benchmarking stats.
"""

from __future__ import annotations

import structlog
import statistics
from collections import defaultdict, deque
from typing import Any

log = structlog.get_logger(__name__)


class PerformanceMonitor:
    """Tracks latency percentiles for model inference."""

    def __init__(self, history_size: int = 1000) -> None:
        self._history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )

    def record_latency(self, model_name: str, latency_ms: float) -> None:
        """Record a single inference latency."""
        self._history[model_name].append(latency_ms)

    def get_stats(self, model_name: str) -> dict[str, float]:
        """Get latency stats (p50, p95, p99) for a model."""
        history = self._history.get(model_name)
        if not history:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}

        sorted_latencies = sorted(history)
        n = len(sorted_latencies)
        
        return {
            "mean": statistics.mean(history),
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)],
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """Get stats for all monitored models."""
        return {
            model: self.get_stats(model)
            for model in self._history.keys()
        }
