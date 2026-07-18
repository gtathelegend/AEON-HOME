"""Inference on the central node.

One ONNX Runtime session, one lag window per device, a device one-hot selecting
the appliance. The node predicts with no PC involved -- the PC is required to
learn, never to run.

Execution providers are tried in order. On the Arduino UNO Q's Dragonwing side
that resolves to CPU on the Cortex-A53 cores, which is what a 6,850-parameter
model needs; QNN is listed first so that the same code accelerates on a part
that has a Hexagon NPU, without pretending the UNO Q is one.
"""

from __future__ import annotations

import time

import numpy as np

PREFERRED_PROVIDERS = ["QNNExecutionProvider", "CPUExecutionProvider"]


class NodeRunner:
    def __init__(self, model_bytes: bytes) -> None:
        import onnxruntime as ort

        available = set(ort.get_available_providers())
        providers = [p for p in PREFERRED_PROVIDERS if p in available] or ["CPUExecutionProvider"]

        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # One window at a time on a small model: threads cost more in handoff
        # than they save in compute.
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1

        self.session = ort.InferenceSession(model_bytes, options, providers=providers)
        self.provider = self.session.get_providers()[0]
        self.input_name = self.session.get_inputs()[0].name
        self.last_us = 0.0

    def run(self, x: np.ndarray) -> tuple[float, float]:
        """[1, 105] -> (p_on, level_z). level_z is normalised to [-1, 1]."""
        t0 = time.perf_counter()
        p_on, level = self.session.run(None, {self.input_name: x.astype(np.float32)})
        self.last_us = (time.perf_counter() - t0) * 1e6
        return float(p_on.ravel()[0]), float(level.ravel()[0])

    def benchmark(self, x: np.ndarray, iterations: int = 200) -> dict:
        """Median, not mean: one scheduling hiccup should not define the number."""
        for _ in range(10):
            self.run(x)                     # warm the session
        samples = []
        for _ in range(iterations):
            self.run(x)
            samples.append(self.last_us)
        samples.sort()
        return {
            "provider": self.provider,
            "iterations": iterations,
            "median_us": samples[len(samples) // 2],
            "p95_us": samples[int(len(samples) * 0.95)],
            "min_us": samples[0],
        }
