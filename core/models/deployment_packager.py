"""
core/models/deployment_packager.py — Assembles a DeploymentPackage from a trained model.

Responsibilities:
  - Read model binary from disk
  - Compute SHA-256 checksum
  - Stamp ModelMetadata with current timestamps
  - Produce a serializable manifest JSON alongside the binary
  - Write manifest to the model directory
"""

from __future__ import annotations

import hashlib
import json
import uuid
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.types.models import (
    DeploymentPackage,
    FeatureCompatibility,
    ModelMetadata,
)
from shared.types.deployment import ActivationState
from shared.errors.model_errors import DeploymentError

log = structlog.get_logger(__name__)

# The firmware version this packager targets (kept in sync with runtime_config.h)
_SUPPORTED_FW_VERSION = "2.0.0"
_MIN_FW_VERSION       = "2.0.0"
_INPUT_SCHEMA_VERSION = 1
_OUTPUT_SCHEMA_VERSION = 1
_COMPATIBILITY_VERSION = 3   # bumped each time schema or feature vector changes


class DeploymentPackager:
    """
    Assembles a self-contained DeploymentPackage from a trained model artifact.

    Usage::

        packager = DeploymentPackager(model_dir=Path("models/"))
        package  = packager.pack("presence_classifier", accuracy=0.91)
        # package.model_binary  — raw bytes ready to send
        # package.to_manifest_dict()  — JSON-serializable summary
    """

    def __init__(self, model_dir: Path) -> None:
        self._model_dir = Path(model_dir)

    # ── Public API ────────────────────────────────────────────────────────────

    def pack(
        self,
        model_name: str,
        accuracy: float = 0.0,
        dataset_version: str = "auto",
        feature_version: str = "v1",
        policy_version: int = 1,
        deployment_version: int | None = None,
        source: str = "learning_loop",
        extra_meta: dict[str, Any] | None = None,
    ) -> DeploymentPackage:
        """
        Build a DeploymentPackage for *model_name*.

        Looks for <model_name>.onnx or <model_name>.bin in model_dir.
        Raises DeploymentError if no binary found.
        """
        binary_path = self._resolve_binary(model_name)
        model_bytes  = binary_path.read_bytes()
        checksum     = _sha256(model_bytes)
        now          = datetime.now(timezone.utc).isoformat()
        package_id   = str(uuid.uuid4())

        if deployment_version is None:
            deployment_version = self._next_deployment_version(model_name)

        metadata = ModelMetadata(
            model_id              = model_name,
            version               = deployment_version,
            training_timestamp    = now,
            dataset_version       = dataset_version,
            feature_version       = feature_version,
            deployment_timestamp  = now,
            deployment_source     = source,
            input_schema_version  = _INPUT_SCHEMA_VERSION,
            output_schema_version = _OUTPUT_SCHEMA_VERSION,
            supported_fw_version  = _SUPPORTED_FW_VERSION,
            min_fw_version        = _MIN_FW_VERSION,
            compatibility_version = _COMPATIBILITY_VERSION,
            checksum              = checksum,
            activation_state      = ActivationState.INACTIVE,
            accuracy_estimate     = accuracy,
        )

        compatibility = FeatureCompatibility(
            required_features   = [
                "temperature", "humidity", "motion",
                "door_open", "mean_temp", "var_temp", "delta_motion",
            ],
            optional_features   = [],
            deprecated_features = [],
            feature_vector_size = 7,
        )

        package = DeploymentPackage(
            package_id         = package_id,
            model              = metadata,
            compatibility      = compatibility,
            model_binary       = model_bytes,
            policy_version     = policy_version,
            deployment_version = deployment_version,
            signature          = _hmac_stub(package_id, checksum),
        )

        self._write_manifest(model_name, deployment_version, package)
        log.info(
            "packager.assembled",
            model=model_name,
            version=deployment_version,
            checksum=checksum[:16] + "…",
            bytes=len(model_bytes),
        )
        return package

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_binary(self, model_name: str) -> Path:
        for ext in (".bin", ".onnx", ".pkl"):
            p = self._model_dir / f"{model_name}{ext}"
            if p.exists():
                return p
        raise DeploymentError(
            f"No model binary found for '{model_name}' in {self._model_dir}",
            context={"model_name": model_name, "model_dir": str(self._model_dir)},
        )

    def _next_deployment_version(self, model_name: str) -> int:
        """Read the version registry JSON, increment, save and return."""
        reg_path = self._model_dir / f"{model_name}_versions.json"
        data = {"current_version": 0, "history": []}
        if reg_path.exists():
            try:
                data = json.loads(reg_path.read_text())
            except Exception:
                pass
        
        next_v = int(data.get("current_version", 0)) + 1
        data["current_version"] = next_v
        
        try:
            reg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
            
        return next_v

    def _write_manifest(
        self,
        model_name: str,
        version: int,
        package: DeploymentPackage,
    ) -> None:
        manifest_path = self._model_dir / f"{model_name}_v{version}_manifest.json"
        manifest_path.write_text(
            json.dumps(package.to_manifest_dict(), indent=2),
            encoding="utf-8",
        )
        log.info("packager.manifest_written", path=str(manifest_path))


# ── Utility ───────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_stub(package_id: str, checksum: str) -> str:
    """Placeholder signature — replace with real HMAC-SHA256 in production."""
    return hashlib.sha256(f"{package_id}:{checksum}".encode()).hexdigest()
