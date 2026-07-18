# backend/aeon/services/authentication_service.py

from __future__ import annotations

import hmac
import hashlib
import time
import structlog
from typing import Any, Dict, Set
from aeon_platform.filesystem.settings import settings
from aeon_platform.security.tokens import verify_token, TokenVerificationError

log = structlog.get_logger(__name__)


class AuthenticationService:
    """
    Subsystem responsible for verifying capability tokens, validating HMAC
    signatures from firmware, and enforcing nonce and timestamp checks.
    """

    def __init__(self, skew_tolerance_s: int = 120) -> None:
        self._skew_tolerance = skew_tolerance_s
        self._used_nonces: Set[str] = set()
        self._secret = getattr(settings, "inter_service_signing_secret", "aeon_secret_key").encode()

    def verify_jwt_token(self, jwt_str: str) -> Dict[str, Any]:
        """Verify standard capability tokens."""
        try:
            return verify_token(jwt_str)
        except TokenVerificationError as e:
            log.warning("auth.jwt_verification_failed", error=str(e))
            raise

    def verify_firmware_hmac(self, payload: str, signature: str, timestamp: int, nonce: str) -> bool:
        """
        Enforce request authenticity from the firmware:
        1. Validate timestamp skew.
        2. Prevent replay attacks via nonce tracking.
        3. Recalculate and compare SHA-256 HMAC.
        """
        now = int(time.time())
        # 1. Timestamp validation
        if abs(now - timestamp) > self._skew_tolerance:
            log.warning("auth.hmac_skew_failed", now=now, packet_ts=timestamp)
            return False

        # 2. Nonce validation
        if nonce in self._used_nonces:
            log.warning("auth.hmac_replay_detected", nonce=nonce)
            return False

        # 3. HMAC calculation
        message = f"{payload}:{timestamp}:{nonce}".encode()
        computed = hmac.new(self._secret, message, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(computed, signature):
            log.warning("auth.hmac_signature_failed")
            return False

        # Record nonce
        self._used_nonces.add(nonce)
        # Prevent unbound memory growth by rolling pruning
        if len(self._used_nonces) > 5000:
            self._used_nonces.clear()

        return True
