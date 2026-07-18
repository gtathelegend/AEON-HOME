"""
aeon/migration/migrator.py — Identity migration orchestrator.

Enables portable identity: a user's preference model, device associations,
and learned behavioural graph can be exported from one ÆON device and
imported on another without any cloud intermediary.

Export format: signed JSON envelope
  {
    "version":    1,
    "device_id":  "<source device>",
    "exported_at": "<iso8601>",
    "profile":    { <NetworkX node-link graph> },
    "signature":  "<JWT of sha256(profile_json)>"
  }

The signature lets the receiving device verify the profile came from a
legitimate ÆON installation and was not tampered with in transit.
"""

from __future__ import annotations

import hashlib
import json
import structlog
from datetime import datetime, timezone
from typing import Any

from aeon_platform.security.tokens import issue_token, verify_token, TokenVerificationError
from aeon_platform.filesystem.settings import settings

log = structlog.get_logger(__name__)


class MigrationError(Exception):
    pass


class Migrator:
    def __init__(self, graph, memory) -> None:
        self._graph  = graph
        self._memory = memory

    async def export(self, user_id: str) -> dict[str, Any]:
        """
        Export user profile as a signed, self-contained migration bundle.
        The bundle can be transferred via QR code, file, or LAN.
        """
        profile = await self._graph.export_profile(user_id)
        if not profile:
            raise MigrationError(f"User '{user_id}' not found in knowledge graph")

        profile_json = json.dumps(profile, sort_keys=True)
        digest = hashlib.sha256(profile_json.encode()).hexdigest()

        # Sign the digest as a capability token so the receiver can verify
        token = issue_token(
            capability="identity.migration",
            confidence=1.0,
            reason=f"sha256={digest}",
            expires_in=86400,   # 24 h — enough time for manual transfer
        )

        bundle = {
            "version":     1,
            "device_id":   settings.device_id,
            "user_id":     user_id,
            "exported_at": datetime.now(tz=timezone.utc).isoformat(),
            "profile":     profile,
            "signature":   token.raw_jwt,
        }
        log.info("migration.export", user_id=user_id, nodes=len(profile.get("nodes", [])))
        return bundle

    async def import_bundle(self, bundle: dict[str, Any]) -> str:
        """
        Validate and import a migration bundle.
        Returns the imported user_id on success.
        Raises MigrationError on invalid/tampered bundles.
        """
        # Verify structure
        required = {"version", "device_id", "user_id", "profile", "signature"}
        if not required.issubset(bundle):
            raise MigrationError("Invalid bundle — missing required fields")

        if bundle["version"] != 1:
            raise MigrationError(f"Unsupported migration bundle version: {bundle['version']}")

        # Verify signature
        try:
            payload = verify_token(bundle["signature"])
        except TokenVerificationError as exc:
            raise MigrationError(f"Bundle signature invalid: {exc}") from exc

        # Verify content digest
        profile_json = json.dumps(bundle["profile"], sort_keys=True)
        digest = hashlib.sha256(profile_json.encode()).hexdigest()
        expected_reason = f"sha256={digest}"
        if payload.get("reason") != expected_reason:
            raise MigrationError("Bundle content digest mismatch — possible tampering")

        # Import graph
        await self._graph.import_profile(bundle["profile"])
        user_id = bundle["user_id"]
        log.info("migration.import", user_id=user_id,
                 source_device=bundle["device_id"],
                 nodes=len(bundle["profile"].get("nodes", [])))
        return user_id
