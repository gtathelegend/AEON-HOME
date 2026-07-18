"""
aeon/learning/dataset.py — Dataset Generator.

Extracts feature vectors from the Memory Store and prepares
X, y matrices for online or batch learning.
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Any
import numpy as np

log = structlog.get_logger(__name__)


class DatasetGenerator:
    """Generates datasets from labelled MemoryStore events."""

    def __init__(self, memory: Any) -> None:
        self._memory = memory

    async def generate(self, since: datetime, limit: int = 1000) -> tuple[np.ndarray, np.ndarray]:
        """
        Fetch labelled samples from memory and convert to X, y matrices.
        
        Returns:
            X: numpy array of shape (N, feature_dim)
            y: numpy array of shape (N,) containing binary labels
        """
        samples = await self._memory.get_labelled_samples(since=since, limit=limit)
        
        if not samples:
            return np.array([]), np.array([])
            
        X_list = []
        y_list = []
        
        for s in samples:
            # We assume features were dumped as a list/dict during the event capture
            feats = s.get("features", [])
            label = s.get("label", 0)
            
            if isinstance(feats, (list, tuple)) and len(feats) == 7:
                X_list.append(feats)
                y_list.append(label)
            elif isinstance(feats, dict):
                # Fallback parse from dict if that's how it was saved
                vec = [
                    feats.get("temperature", 0.0),
                    feats.get("humidity", 0.0),
                    float(feats.get("motion", 0)),
                    float(feats.get("door_open", 0)),
                    feats.get("mean_temp", 0.0),
                    feats.get("var_temp", 0.0),
                    feats.get("delta_motion", 0.0),
                ]
                X_list.append(vec)
                y_list.append(label)
                
        if not X_list:
            return np.array([]), np.array([])
            
        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.int32)
        
        log.info("dataset_generator.generated", samples=len(y))
        return X, y
