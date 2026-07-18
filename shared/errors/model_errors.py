# shared/errors/model_errors.py
"""
Domain exceptions for the model lifecycle and AI runtime.

All errors include a human-readable `detail` message and an optional
`context` dict for structured logging.
"""
from __future__ import annotations
from typing import Any


class AeonModelError(Exception):
    """Base class for all model lifecycle errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail  = message
        self.context = context or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.detail!r}, ctx={self.context})"


class ModelLoadError(AeonModelError):
    """Raised when a model binary cannot be loaded or parsed."""


class DeploymentError(AeonModelError):
    """Raised when a deployment lifecycle operation fails."""


class CompatibilityError(AeonModelError):
    """Raised when a deployment package is incompatible with firmware or schema."""


class ValidationError(AeonModelError):
    """Raised when deployment package validation fails (checksum, schema, etc.)."""


class InferenceRuntimeError(AeonModelError):
    """Raised when the inference runtime encounters an unrecoverable error."""


class StatisticsError(AeonModelError):
    """Raised when statistics collection or persistence fails."""


class RollbackError(AeonModelError):
    """Raised when a rollback operation cannot be completed."""


class LearningBufferError(AeonModelError):
    """Raised when the learning data buffer encounters an error."""
