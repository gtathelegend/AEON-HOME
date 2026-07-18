"""
aeon/qnn/session.py — NPU Session Manager.

Wraps the underlying QNN or ONNX runtime sessions, handling lifecycle,
safe unloading, and threading locks.
"""

from __future__ import annotations

import structlog
import threading
from typing import Any

log = structlog.get_logger(__name__)

# QNN is optional
try:
    import qnn  # type: ignore[import]
    _QNN_AVAILABLE = True
except ImportError:
    _QNN_AVAILABLE = False


class SessionManager:
    """Manages active inference sessions and safely hot-reloads them."""

    def __init__(self, use_npu: bool) -> None:
        self._use_npu = use_npu and _QNN_AVAILABLE
        self._sessions: dict[str, Any] = {}
        # Locks per model to ensure we don't infer while hot-reloading
        self._locks: dict[str, threading.Lock] = {}
        
    @property
    def active_models(self) -> list[str]:
        return list(self._sessions.keys())
        
    def add_session(self, name: str, session: Any) -> None:
        """Register a new session."""
        if name not in self._locks:
            self._locks[name] = threading.Lock()
            
        with self._locks[name]:
            # If replacing an existing QNN session, we'd explicitly free it here
            self._sessions[name] = session
            log.info("qnn_session.registered", name=name)

    def get_session(self, name: str) -> Any:
        """Retrieve a session. Caller must acquire lock if needed."""
        return self._sessions.get(name)

    def get_lock(self, name: str) -> threading.Lock:
        """Get the execution lock for a model."""
        if name not in self._locks:
            self._locks[name] = threading.Lock()
        return self._locks[name]

    def remove_session(self, name: str) -> bool:
        """Safely remove a session."""
        if name not in self._sessions:
            return False
            
        with self.get_lock(name):
            session = self._sessions.pop(name)
            if self._use_npu and isinstance(session, qnn.ModelContext): # type: ignore
                # QNN contexts support explicit free/unload if needed
                pass
            log.info("qnn_session.removed", name=name)
        return True
