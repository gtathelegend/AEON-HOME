"""
backend/aeon/models/manager.py — Full model lifecycle state machine.

Tracks installed models, active model, candidate model, previous model,
rollback target, deployment history, runtime statistics, and validation
status. Wraps QNNManager for low-level inference execution.
"""

from __future__ import annotations

import structlog
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from shared.types.deployment import (
    ActivationState,
    DeploymentRecord,
    DeploymentState,
    RollbackReason,
)
from shared.types.models import ModelMetadata, RuntimeStatistics, ModelScore
from shared.errors.model_errors import RollbackError, ModelLoadError

if TYPE_CHECKING:
    from aeon_platform.runtime.qnn.manager import QNNManager
    from shared.types.models import DeploymentPackage

log = structlog.get_logger(__name__)

# Maximum number of deployment records to retain in memory
_MAX_HISTORY = 20


class ModelManager:
    """
    Full model lifecycle state machine.

    Single point of truth for:
      - installed_models  : list of known model names
      - active_model      : currently running model metadata
      - candidate_model   : staged but not yet committed model
      - previous_model    : last committed model (rollback target)
      - deployment_history: list[DeploymentRecord]
      - runtime_statistics: RuntimeStatistics (live)
      - validation_status : result of last validation
    """

    def __init__(self, qnn: "QNNManager", model_dir: Path) -> None:
        self._qnn       = qnn
        self._model_dir = Path(model_dir)

        # ── Lifecycle state ───────────────────────────────────────────────────
        self.active_model:      Optional[ModelMetadata]   = None
        self.candidate_model:   Optional[ModelMetadata]   = None
        self.previous_model:    Optional[ModelMetadata]   = None
        self.deployment_history: list[DeploymentRecord]   = []
        self.runtime_statistics: RuntimeStatistics        = RuntimeStatistics()
        self.validation_status: Optional[str]             = None
        self._deployment_state: DeploymentState           = DeploymentState.RUNNING
        self._current_score:    Optional[ModelScore]      = None

    # ── QNNManager delegation (unchanged surface) ─────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """
        Full status dict understood by WebSocket bus and system route.

        Keys:
          backend        — "QNN_HTP" | "ONNX" | "UNAVAILABLE"
          active_models  — list[str]
          metadata       — dict
          metrics        — {model_name: {mean, p50, p95, p99}}
          deployment     — current deployment lifecycle info
        """
        base = self._qnn.get_status()
        base["deployment"] = self.get_deployment_status()
        base["active_model_metadata"] = (
            self.active_model.to_dict() if self.active_model else None
        )
        base["statistics"] = self.runtime_statistics.to_dict()
        base["score"] = self._current_score.to_dict() if self._current_score else None
        return base

    def list_models(self) -> list[dict[str, Any]]:
        """List all loaded models with file metadata."""
        status = self._qnn.get_status()
        models = []
        for name in status.get("active_models", []):
            bin_path  = self._model_dir / f"{name}.bin"
            onnx_path = self._model_dir / f"{name}.onnx"

            size = 0
            fmt  = "unknown"
            if bin_path.exists():
                size = bin_path.stat().st_size
                fmt  = "QNN (.bin)"
            elif onnx_path.exists():
                size = onnx_path.stat().st_size
                fmt  = "ONNX (.onnx)"

            meta = status.get("metadata", {}).get(name, {})
            models.append({
                "name":       name,
                "format":     fmt,
                "size_bytes": size,
                "status":     "loaded",
                "loaded_at":  meta.get("loaded_at"),
            })
        return models

    async def reload_model(self, name: str) -> bool:
        """Hot-reload a model from disk (e.g. after learning updates)."""
        log.info("model_manager.reload", name=name)
        return await self._qnn.reload_model(name)

    # ── Deployment lifecycle ──────────────────────────────────────────────────

    def begin_deployment(self, package: "DeploymentPackage") -> DeploymentRecord:
        """
        Stage a new candidate deployment.
        Transitions: * → VALIDATING (caller must call commit or rollback).
        """
        self._deployment_state = DeploymentState.VALIDATING
        self.candidate_model   = package.model

        record = DeploymentRecord(
            deployment_id = package.package_id,
            model_id      = package.model.model_id,
            model_version = package.model.version,
            state         = DeploymentState.VALIDATING,
            started_at    = datetime.now(timezone.utc),
            checksum      = package.model.checksum,
            source        = package.model.deployment_source,
        )
        self._push_history(record)
        log.info(
            "model_manager.deployment_started",
            package_id=package.package_id,
            model=package.model.model_id,
            version=package.model.version,
        )
        return record

    def commit_deployment(self) -> None:
        """
        Activate the candidate model and promote the current active to previous.
        Transitions: VALIDATING → RUNNING.
        """
        if self.candidate_model is None:
            raise ModelLoadError("No candidate model staged for commit")

        self.previous_model  = self.active_model
        self.active_model    = self.candidate_model
        self.candidate_model = None

        if self.active_model:
            self.active_model.activation_state = ActivationState.ACTIVE
        if self.previous_model:
            self.previous_model.activation_state = ActivationState.PREVIOUS

        self._deployment_state   = DeploymentState.RUNNING
        self.runtime_statistics  = RuntimeStatistics()  # reset stats for new model

        self._update_last_record(DeploymentState.RUNNING)
        log.info(
            "model_manager.deployment_committed",
            model=self.active_model.model_id if self.active_model else None,
            version=self.active_model.version if self.active_model else None,
        )

    def rollback(self, reason: RollbackReason = RollbackReason.MANUAL_ROLLBACK) -> None:
        """
        Rollback to the previous model (or discard candidate).
        Transitions: * → ROLLEDBACK.
        """
        if self.previous_model is None and self.candidate_model is None:
            raise RollbackError(
                "No previous model available for rollback",
                context={"reason": reason.value},
            )

        if self.candidate_model is not None:
            # Discard staged candidate — reactivate active
            log.info(
                "model_manager.rollback_candidate",
                reason=reason.value,
                candidate=self.candidate_model.model_id,
            )
            self.candidate_model = None
        else:
            # Full rollback: restore previous
            log.warning(
                "model_manager.rollback_active",
                reason=reason.value,
                active=self.active_model.model_id if self.active_model else None,
                previous=self.previous_model.model_id if self.previous_model else None,
            )
            self.active_model    = self.previous_model
            self.previous_model  = None

        self._deployment_state = DeploymentState.ROLLEDBACK
        self._update_last_record(DeploymentState.ROLLEDBACK, reason=reason)

    def fail_deployment(self, error: str) -> None:
        """Mark the current deployment attempt as failed."""
        self._deployment_state = DeploymentState.FAILED
        self.candidate_model   = None
        self._update_last_record(DeploymentState.FAILED, error_message=error)
        log.error("model_manager.deployment_failed", error=error)

    # ── Statistics & Scoring ──────────────────────────────────────────────────

    def record_inference(
        self,
        confidence: float,
        latency_ms: float,
        success: bool = True,
    ) -> None:
        """Update live runtime statistics after each inference."""
        self.runtime_statistics.record_inference(confidence, latency_ms, success)
        if self.active_model:
            self.active_model.inference_count       = self.runtime_statistics.total_inference_count
            self.active_model.avg_confidence        = self.runtime_statistics.avg_confidence
            self.active_model.avg_latency_ms        = self.runtime_statistics.avg_latency_ms
            self.active_model.last_updated          = datetime.now(timezone.utc).isoformat()

    def update_score(self, score: ModelScore) -> None:
        """Store the latest composite model score."""
        self._current_score = score
        log.debug("model_manager.score_updated", composite=score.composite_score)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_deployment_status(self) -> dict[str, Any]:
        return {
            "state":          self._deployment_state.value,
            "active_model":   self.active_model.to_dict() if self.active_model else None,
            "candidate_model": self.candidate_model.to_dict() if self.candidate_model else None,
            "previous_model": self.previous_model.to_dict() if self.previous_model else None,
            "rollback_available": self.previous_model is not None,
            "validation_status":  self.validation_status,
        }

    def get_inventory(self) -> list[dict[str, Any]]:
        """All known model metadata entries with their activation state."""
        inventory = []
        for meta in filter(None, [self.active_model, self.candidate_model, self.previous_model]):
            inventory.append(meta.to_dict())
        return inventory

    def get_deployment_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.deployment_history[-limit:]]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _push_history(self, record: DeploymentRecord) -> None:
        self.deployment_history.append(record)
        if len(self.deployment_history) > _MAX_HISTORY:
            self.deployment_history = self.deployment_history[-_MAX_HISTORY:]

    def _update_last_record(
        self,
        state: DeploymentState,
        reason: Optional[RollbackReason] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if not self.deployment_history:
            return
        rec = self.deployment_history[-1]
        rec.state          = state
        rec.completed_at   = datetime.now(timezone.utc)
        rec.rollback_reason = reason
        rec.error_message  = error_message
