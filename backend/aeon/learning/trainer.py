"""
aeon/learning/trainer.py — Incremental edge trainer.

Simulates parameter-efficient fine tuning (PEFT) on edge devices.
For the hackathon, we use SGDClassifier with log_loss to simulate updating
the final classification layer of a larger frozen neural network.
"""

from __future__ import annotations

import structlog
import pickle
from pathlib import Path
import numpy as np

# scikit-learn is used for the edge simulation
from sklearn.linear_model import SGDClassifier

log = structlog.get_logger(__name__)


class IncrementalTrainer:
    """Performs online learning on continuous data streams."""

    def __init__(self, state_path: Path) -> None:
        self._state_path = state_path
        self._model: SGDClassifier | None = None
        self._threshold: float = 0.75
        self._load_or_init()

    @property
    def threshold(self) -> float:
        return self._threshold

    def update_threshold(self, delta: float) -> None:
        self._threshold = max(0.1, min(0.95, self._threshold + delta))

    def _load_or_init(self) -> None:
        """Load existing SGD state or initialize a fresh one."""
        if self._state_path.exists():
            try:
                with open(self._state_path, "rb") as f:
                    self._model = pickle.load(f)
                log.info("incremental_trainer.loaded", path=str(self._state_path))
                return
            except Exception:
                log.exception("incremental_trainer.load_failed")
                
        # Initialize fresh
        self._model = SGDClassifier(loss='log_loss', learning_rate='adaptive', eta0=0.01)
        # We must explicitly initialize classes [0, 1] for partial_fit
        # Dummy fit to initialize weights for 7 features
        dummy_X = np.zeros((2, 7), dtype=np.float32)
        dummy_y = np.array([0, 1])
        self._model.partial_fit(dummy_X, dummy_y, classes=np.array([0, 1]))
        log.info("incremental_trainer.initialized")

    def train_batch(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """
        Perform an incremental partial_fit update.
        Returns training metrics.
        """
        if len(X) == 0:
            return {"loss": 0.0, "accuracy": 0.0}
            
        self._model.partial_fit(X, y)
        
        # Calculate training accuracy
        acc = self._model.score(X, y)
        
        # Save state
        with open(self._state_path, "wb") as f:
            pickle.dump(self._model, f)
            
        log.info("incremental_trainer.update", samples=len(y), acc=acc)
        return {"accuracy": float(acc)}

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> float:
        """Evaluate the model against a holdout dataset."""
        if len(X_test) == 0:
            return 1.0  # Default if no test data
        return float(self._model.score(X_test, y_test))

    def export_weights(self) -> np.ndarray:
        """Extract the final layer weights (coef_ and intercept_)."""
        # Shape: (1, 7) and (1,)
        w = self._model.coef_
        b = self._model.intercept_
        # Combine or return as needed for QNN compilation/ONNX export
        # For simulation, we just return the weights
        return np.concatenate((w.flatten(), b))
