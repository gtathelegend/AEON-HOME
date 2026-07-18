"""
backend/aeon/models/deployment_service.py — Orchestrates server-side deployment lifecycle.

Responsibilities:
  - Receive a DeploymentPackage upload (via API)
  - Run DeploymentValidator checks
  - Transition ModelManager through deployment states
  - Broadcast deployment events to firmware over WebSocket bus
  - Expose deployment status for the API layer
"""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.models.deployment_validator import DeploymentValidator
from shared.types.deployment import DeploymentState, RollbackReason
from shared.errors.model_errors import (
    DeploymentError,
    ValidationError,
    CompatibilityError,
    RollbackError,
)

if TYPE_CHECKING := True:
    from backend.aeon.models.manager import ModelManager
    from shared.types.models import DeploymentPackage

log = structlog.get_logger(__name__)


class DeploymentService:
    """
    Orchestrates a full deployment cycle:

      1. Validate (DeploymentValidator)
      2. Stage candidate in ModelManager
      3. Notify firmware: `deployment_started`
      4. Firmware loads and acks: `deployment_ack`
      5. Commit activation in ModelManager
      6. Broadcast: `deployment_completed` / `model_activated`

    Rollback:
      - Called on validation failure, firmware rejection, or explicit request
      - Restores previous model in ModelManager
      - Broadcasts: `deployment_failed` / `model_rolled_back`
    """

    def __init__(
        self,
        model_manager: "ModelManager",
        ws_bus: Any,
        validator: Optional[DeploymentValidator] = None,
    ) -> None:
        self._manager   = model_manager
        self._ws_bus    = ws_bus
        self._validator = validator or DeploymentValidator()
        self._lock      = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    async def deploy(self, package: "DeploymentPackage") -> dict[str, Any]:
        """
        Execute a full deployment lifecycle.

        Returns a status dict with `success` and `deployment_id`.
        On failure, raises DeploymentError.
        """
        async with self._lock:
            return await self._deploy_inner(package)

    async def rollback(
        self,
        reason: RollbackReason = RollbackReason.MANUAL_ROLLBACK,
    ) -> dict[str, Any]:
        """Trigger a rollback to the previous model."""
        async with self._lock:
            return await self._rollback_inner(reason)

    def get_status(self) -> dict[str, Any]:
        return self._manager.get_deployment_status()

    # ── Lifecycle implementation ──────────────────────────────────────────────

    async def _deploy_inner(self, package: "DeploymentPackage") -> dict[str, Any]:
        pkg_id  = package.package_id
        model   = package.model

        log.info(
            "deployment_service.starting",
            package_id=pkg_id,
            model=model.model_id,
            version=model.version,
        )

        # ── Stage 1: Validate ─────────────────────────────────────────────────
        try:
            self._validator.validate(package)
            self._manager.validation_status = "passed"
        except (ValidationError, CompatibilityError) as exc:
            self._manager.validation_status = f"failed: {exc.detail}"
            self._manager.fail_deployment(str(exc.detail))
            await self._broadcast("deployment_failed", {
                "deployment_id": pkg_id,
                "reason":        str(exc.detail),
                "model_id":      model.model_id,
                "version":       model.version,
            })
            raise DeploymentError(
                f"Deployment {pkg_id} rejected during validation: {exc.detail}",
                context={"package_id": pkg_id},
            ) from exc

        # ── Stage 2: Stage candidate ──────────────────────────────────────────
        record = self._manager.begin_deployment(package)

        # ── Stage 3: Notify firmware ──────────────────────────────────────────
        await self._broadcast("deployment_started", {
            "deployment_id": pkg_id,
            "model_id":      model.model_id,
            "version":       model.version,
            "checksum":      model.checksum,
            "feature_version": model.feature_version,
        })

        # ── Stage 4: Wait for firmware ack (fire-and-forget in simulation) ────
        # In production the firmware sends a `deployment_ack` WebSocket message
        # which the bus routes back to this service. For now we proceed directly
        # after a short yield so the event loop can process pending WS frames.
        await asyncio.sleep(0)

        # ── Stage 5: Commit ───────────────────────────────────────────────────
        try:
            self._manager.commit_deployment()
        except Exception as exc:
            self._manager.fail_deployment(str(exc))
            await self._broadcast("deployment_failed", {
                "deployment_id": pkg_id,
                "reason": str(exc),
            })
            raise DeploymentError(
                f"Deployment {pkg_id} failed during activation: {exc}",
            ) from exc

        # ── Stage 6: Broadcast success ────────────────────────────────────────
        await self._broadcast("deployment_completed", {
            "deployment_id": pkg_id,
            "model_id":      model.model_id,
            "version":       model.version,
        })
        await self._broadcast("model_activated", {
            "model_id": model.model_id,
            "version":  model.version,
        })

        log.info(
            "deployment_service.completed",
            package_id=pkg_id,
            model=model.model_id,
            version=model.version,
        )
        return {
            "success":       True,
            "deployment_id": pkg_id,
            "model_id":      model.model_id,
            "version":       model.version,
            "state":         DeploymentState.RUNNING.value,
        }

    async def _rollback_inner(self, reason: RollbackReason) -> dict[str, Any]:
        try:
            self._manager.rollback(reason)
        except RollbackError as exc:
            raise DeploymentError(
                f"Rollback failed: {exc.detail}",
                context=exc.context,
            ) from exc

        rolled_back_to = self._manager.active_model
        await self._broadcast("model_rolled_back", {
            "reason":   reason.value,
            "model_id": rolled_back_to.model_id if rolled_back_to else None,
            "version":  rolled_back_to.version  if rolled_back_to else None,
        })

        log.info(
            "deployment_service.rollback_complete",
            reason=reason.value,
            active_model=rolled_back_to.model_id if rolled_back_to else None,
        )
        return {
            "success":      True,
            "reason":       reason.value,
            "active_model": rolled_back_to.to_dict() if rolled_back_to else None,
            "state":        DeploymentState.ROLLEDBACK.value,
        }

    async def _broadcast(self, event: str, payload: dict[str, Any]) -> None:
        try:
            await self._ws_bus.publish(event, payload)
        except Exception:
            log.exception("deployment_service.broadcast_error", event=event)
