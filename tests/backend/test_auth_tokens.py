"""
tests/backend/test_auth_tokens.py

Unit tests for the capability token system.
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest
from aeon.auth.tokens import issue_token, verify_token, TokenVerificationError


def test_issue_and_verify():
    token = issue_token(
        capability="presence.detected",
        confidence=0.92,
        reason="motion + high presence_prob",
    )
    assert token.token_id
    payload = verify_token(token.raw_jwt)
    assert payload["capability"] == "presence.detected"
    assert abs(payload["confidence"] - 0.92) < 0.001


def test_expired_token_raises():
    token = issue_token(
        capability="door.open",
        confidence=0.8,
        reason="test",
        expires_in=1,    # 1 second TTL
    )
    time.sleep(2)
    with pytest.raises(TokenVerificationError):
        verify_token(token.raw_jwt)


def test_tampered_token_raises():
    token = issue_token(capability="test", confidence=0.5, reason="test")
    tampered = token.raw_jwt[:-4] + "XXXX"
    with pytest.raises(TokenVerificationError):
        verify_token(tampered)


def test_token_fields():
    token = issue_token(capability="anomaly.detected", confidence=0.99, reason="score=0.99")
    assert token.device_id  # from settings.device_id
    assert token.expires_at > token.issued_at
