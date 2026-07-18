"""
aeon/qnn/tensor.py — Tensor conversion and preprocessing.

Handles data normalization and scaling for QNN/ONNX models.
"""

from __future__ import annotations

import structlog
import numpy as np

log = structlog.get_logger(__name__)


class TensorProcessor:
    """Preprocesses input data and postprocesses output tensors."""

    def preprocess(self, model_name: str, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Convert input data to the required tensor format."""
        processed = {}
        for name, data in inputs.items():
            # For this demo, all our models expect float32
            # If QNN INT8 quantization were enabled, scaling would happen here
            processed[name] = data.astype(np.float32)
        return processed

    def postprocess(self, model_name: str, outputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Convert raw tensor outputs to usable data."""
        processed = {}
        for name, data in outputs.items():
            # Apply softmax or thresholding if required by the model
            # For our current models, raw scores (probabilities/anomaly scores) are fine
            processed[name] = data
        return processed
