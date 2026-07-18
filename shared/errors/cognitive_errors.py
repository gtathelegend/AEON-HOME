# shared/errors/cognitive_errors.py

from __future__ import annotations


class CognitiveError(Exception):
    """Base error for all cognitive operating system subsystems."""
    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ReasoningError(CognitiveError):
    """Raised when the Reasoning Engine encounters evaluation or ranking anomalies."""
    pass


class MemoryError(CognitiveError):
    """Raised on memory store, retrieval, or retention GC failures."""
    pass


class KnowledgeError(CognitiveError):
    """Raised on Knowledge Base integration conflicts or resolution bugs."""
    pass


class ExplanationError(CognitiveError):
    """Raised when building human-readable summaries or reason codes fails."""
    pass


class DeviceRegistryError(CognitiveError):
    """Raised when device registration, health ping, or capability checking fails."""
    pass


class EvidenceError(CognitiveError):
    """Raised when evidence items violate validation constraints."""
    pass


class ConfidenceError(CognitiveError):
    """Raised when confidence score calculations overflow or violate bounds."""
    pass
