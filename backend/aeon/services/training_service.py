# backend/aeon/services/training_service.py

from __future__ import annotations

import structlog
from typing import Any, Dict

log = structlog.get_logger(__name__)


class TrainingService:
    """Service layer managing autonomous retraining triggering and progress monitoring."""

    def __init__(self, learning_loop: Any) -> None:
        self._loop = learning_loop

    def trigger_retraining(self) -> Dict[str, Any]:
        if not self._loop:
            return {"status": "error", "message": "Learning loop not available"}

        self._loop.trigger_retrain()
        return {
            "status": self._loop.training_state,
            "progress_pct": self._loop.adaptation_progress_pct,
        }

    def get_status(self) -> Dict[str, Any]:
        if not self._loop:
            return {"training_state": "unavailable"}
        return {
            "training_state": self._loop.training_state,
            "progress_pct": self._loop.adaptation_progress_pct,
            "last_train_ts": self._loop.last_train_ts,
        }
