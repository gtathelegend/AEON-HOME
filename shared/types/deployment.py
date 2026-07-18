# shared/types/deployment.py
"""
Deployment lifecycle types shared between backend and tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DeploymentState(str, Enum):
    """States in the model deployment lifecycle."""
    RECEIVING   = "receiving"
    VALIDATING  = "validating"
    INSTALLING  = "installing"
    VERIFYING   = "verifying"
    ACTIVATING  = "activating"
    RUNNING     = "running"
    ROLLEDBACK  = "rolledback"
    FAILED      = "failed"


class RollbackReason(str, Enum):
    """Reasons that triggered an automatic rollback."""
    ACTIVATION_FAILED       = "activation_failed"
    RUNTIME_CRASH           = "runtime_crash"
    CONFIDENCE_COLLAPSED    = "confidence_collapsed"
    LATENCY_EXCEEDED        = "latency_exceeded"
    DEPLOYMENT_CORRUPTED    = "deployment_corrupted"
    MODEL_INVALID           = "model_invalid"
    MANUAL_ROLLBACK         = "manual_rollback"
    CHECKSUM_MISMATCH       = "checksum_mismatch"
    COMPATIBILITY_MISMATCH  = "compatibility_mismatch"


class ActivationState(str, Enum):
    """Current activation state of a model instance."""
    INACTIVE  = "inactive"
    CANDIDATE = "candidate"
    ACTIVE    = "active"
    PREVIOUS  = "previous"
    FAILED    = "failed"


@dataclass
class DeploymentRecord:
    """Immutable record of a single deployment lifecycle event."""
    deployment_id:   str
    model_id:        str
    model_version:   int
    state:           DeploymentState
    started_at:      datetime
    completed_at:    Optional[datetime] = None
    rollback_reason: Optional[RollbackReason] = None
    error_message:   Optional[str] = None
    checksum:        Optional[str] = None
    source:          str = "unknown"

    def to_dict(self) -> dict:
        return {
            "deployment_id":   self.deployment_id,
            "model_id":        self.model_id,
            "model_version":   self.model_version,
            "state":           self.state.value,
            "started_at":      self.started_at.isoformat(),
            "completed_at":    self.completed_at.isoformat() if self.completed_at else None,
            "rollback_reason": self.rollback_reason.value if self.rollback_reason else None,
            "error_message":   self.error_message,
            "checksum":        self.checksum,
            "source":          self.source,
        }
