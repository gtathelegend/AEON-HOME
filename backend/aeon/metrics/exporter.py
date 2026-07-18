"""
aeon/metrics/exporter.py — Prometheus-compatible telemetry exporter.

Exposes /metrics on settings.metrics_port (default 9090).
All metrics are computed from local data — nothing is pushed to any cloud.

NPU utilization note: The Hexagon DSP does not expose utilization via
standard psutil/OS APIs. sys_npu_utilization is therefore an ESTIMATE
derived from CPU load (known to correlate on Snapdragon X Elite workloads).
It is clearly labelled "estimated" in the dashboard. No random noise is added.
"""

from __future__ import annotations

import asyncio
import structlog
import psutil
from pathlib import Path

from prometheus_client import Counter, Gauge, start_http_server

from aeon_platform.filesystem.settings import settings

log = structlog.get_logger(__name__)

# ── Metric definitions ────────────────────────────────────────────────────────

frames_total = Counter(
    "aeon_feature_frames_total",
    "Feature frames received from Arduino Sentinel",
)
decisions_total = Counter(
    "aeon_decisions_total",
    "Policy decisions made",
    labelnames=["action"],
)
anomaly_score = Gauge(
    "aeon_anomaly_score",
    "Latest anomaly score from QNN inference",
)
recovery_latency_ms = Gauge(
    "aeon_recovery_latency_ms",
    "Last EEPROM state recovery latency in milliseconds",
)
memory_db_size = Gauge(
    "aeon_memory_db_size_bytes",
    "SQLite memory store file size in bytes",
)
ws_clients = Gauge(
    "aeon_ws_clients",
    "Number of connected WebSocket clients",
)
learning_train_total = Counter(
    "aeon_learning_train_total",
    "Number of on-device training iterations completed",
)
privacy_bytes_saved = Counter(
    "aeon_privacy_bytes_saved",
    "Bytes of raw sensor data processed locally instead of streamed externally",
)

# System / hardware metrics
sys_cpu_utilization = Gauge(
    "aeon_sys_cpu_utilization",
    "CPU utilization percentage (real, from psutil)",
)
sys_npu_utilization = Gauge(
    "aeon_sys_npu_utilization",
    "NPU utilization percentage (ESTIMATED — Hexagon DSP not directly readable via psutil)",
)
sys_ram_utilization = Gauge(
    "aeon_sys_ram_utilization",
    "RAM utilization percentage (real, from psutil)",
)
sys_power_draw_w = Gauge(
    "aeon_sys_power_draw_w",
    "Estimated system power draw in Watts (formula-based estimate; not from hardware sensor)",
)
inference_latency_ms = Gauge(
    "aeon_inference_latency_ms",
    "Model inference latency (real, from QNN performance monitor)",
)


class MetricsExporter:
    async def run(self) -> None:
        start_http_server(settings.metrics_port)
        log.info("metrics.listening", port=settings.metrics_port)
        while True:
            self._collect_system_metrics()
            await asyncio.sleep(1)

    def _collect_system_metrics(self) -> None:
        # ── Database size ─────────────────────────────────────────────────────
        db = Path(settings.memory_db_path)
        if db.exists():
            memory_db_size.set(db.stat().st_size)

        # ── Real CPU and RAM from psutil ──────────────────────────────────────
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        sys_cpu_utilization.set(cpu)
        sys_ram_utilization.set(ram)

        # ── NPU utilization — ESTIMATE, no random noise ───────────────────────
        # Hexagon DSP utilization is not readable via standard Python APIs.
        # We use a deterministic proxy: 40% of CPU load, floored at 0, capped at 100.
        # This is labelled as "estimated" everywhere it appears in the UI.
        npu_est = min(100.0, max(0.0, cpu * 0.4))
        sys_npu_utilization.set(npu_est)

        # ── Power draw — formula estimate, no random noise ────────────────────
        # Base idle draw (Snapdragon X Elite ~15 W) + dynamic component from load.
        # Not from a hardware power sensor — labelled as estimated in UI.
        power_est = 15.0 + ((cpu + npu_est) / 200.0) * 10.0
        sys_power_draw_w.set(power_est)
