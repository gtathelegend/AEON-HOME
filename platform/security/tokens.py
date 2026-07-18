# platform/security/tokens.py

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from pydantic import BaseModel

from platform.filesystem.settings import settings


class CapabilityToken(BaseModel):
    token_id:   str
    device_id:  str
    capability: str          # e.g. "presence.detected", "door.open"
    confidence: float
    reason:     str
    issued_at:  datetime
    expires_at: datetime
    raw_jwt:    str


class TokenVerificationError(Exception):
    pass


def issue_token(
    capability: str,
    confidence: float,
    reason: str,
    expires_in: int | None = None,
) -> CapabilityToken:
    """
    Issue a signed capability token.

    Args:
        capability:  dot-namespaced capability string
        confidence:  AI confidence score (0.0–1.0)
        reason:      human-readable decision reason
        expires_in:  TTL in seconds (defaults to settings.jwt_expire_s)
    """
    now     = datetime.now(tz=timezone.utc)
    exp     = now + timedelta(seconds=expires_in or settings.jwt_expire_s)
    tok_id  = str(uuid.uuid4())

    payload = {
        "jti":        tok_id,
        "sub":        settings.device_id,
        "capability": capability,
        "confidence": round(confidence, 4),
        "reason":     reason,
        "iat":        int(now.timestamp()),
        "exp":        int(exp.timestamp()),
    }
    raw = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return CapabilityToken(
        token_id=tok_id,
        device_id=settings.device_id,
        capability=capability,
        confidence=confidence,
        reason=reason,
        issued_at=now,
        expires_at=exp,
        raw_jwt=raw,
    )


def verify_token(raw_jwt: str) -> dict[str, Any]:
    """
    Verify and decode a capability token.

    Raises TokenVerificationError on failure.
    Returns the decoded payload dict on success.
    """
    try:
        payload = jwt.decode(
            raw_jwt,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        raise TokenVerificationError(str(exc)) from exc
