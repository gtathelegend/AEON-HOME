"""
core/models/deployment_validator.py — Validates a DeploymentPackage before activation.

Checks (in order):
  1. Checksum integrity (SHA-256 of binary matches manifest)
  2. Metadata completeness (all required fields present)
  3. Schema compatibility (input/output schema versions)
  4. Firmware compatibility (firmware version >= min_fw_version)
  5. Feature compatibility (required features subset of firmware features)
  6. Model integrity (binary is non-empty, not obviously corrupted)

All failures raise typed exceptions from shared.errors.model_errors.
"""

from __future__ import annotations

import hashlib
import re
import structlog
from typing import Sequence

from shared.types.models import DeploymentPackage, ModelMetadata
from shared.errors.model_errors import (
    ValidationError,
    CompatibilityError,
)

log = structlog.get_logger(__name__)

# Features exposed by the firmware feature extractor — must stay in sync
# with the features produced by feature_extractor.cpp
_FIRMWARE_FEATURES: frozenset[str] = frozenset({
    "temperature", "humidity", "motion",
    "door_open", "mean_temp", "var_temp", "delta_motion",
})

_CURRENT_INPUT_SCHEMA_VERSION  = 1
_CURRENT_OUTPUT_SCHEMA_VERSION = 1
_FIRMWARE_VERSION              = "2.0.0"


class DeploymentValidator:
    """
    Validates a DeploymentPackage against runtime constraints.

    Usage::

        validator = DeploymentValidator()
        validator.validate(package)   # raises on failure, returns None on success
    """

    def __init__(
        self,
        firmware_version: str = _FIRMWARE_VERSION,
        firmware_features: frozenset[str] | None = None,
    ) -> None:
        self._fw_version  = firmware_version
        self._fw_features = firmware_features or _FIRMWARE_FEATURES

    def validate(self, package: DeploymentPackage) -> None:
        """
        Run all validation checks in sequence.
        Raises ValidationError or CompatibilityError on failure.
        """
        self._check_checksum(package)
        self._check_metadata(package.model)
        self._check_schema_versions(package.model)
        self._check_firmware_compatibility(package.model)
        self._check_feature_compatibility(package)
        self._check_model_integrity(package)
        log.info(
            "validator.ok",
            package_id=package.package_id,
            model=package.model.model_id,
            version=package.model.version,
        )

    # ── Checks ────────────────────────────────────────────────────────────────

    def _check_checksum(self, package: DeploymentPackage) -> None:
        computed = hashlib.sha256(package.model_binary).hexdigest()
        if computed != package.model.checksum:
            raise ValidationError(
                "Checksum mismatch — deployment binary may be corrupted",
                context={
                    "expected": package.model.checksum,
                    "computed": computed,
                    "package_id": package.package_id,
                },
            )

    def _check_metadata(self, meta: ModelMetadata) -> None:
        required = [
            "model_id", "version", "training_timestamp",
            "dataset_version", "feature_version",
            "deployment_timestamp", "deployment_source",
            "checksum", "activation_state",
        ]
        missing = [f for f in required if not getattr(meta, f, None)]
        if missing:
            raise ValidationError(
                f"Deployment metadata missing fields: {missing}",
                context={"missing_fields": missing},
            )

    def _check_schema_versions(self, meta: ModelMetadata) -> None:
        if meta.input_schema_version != _CURRENT_INPUT_SCHEMA_VERSION:
            raise CompatibilityError(
                f"Input schema version mismatch: model={meta.input_schema_version}, "
                f"runtime={_CURRENT_INPUT_SCHEMA_VERSION}",
                context={"model_schema": meta.input_schema_version,
                         "runtime_schema": _CURRENT_INPUT_SCHEMA_VERSION},
            )
        if meta.output_schema_version != _CURRENT_OUTPUT_SCHEMA_VERSION:
            raise CompatibilityError(
                f"Output schema version mismatch: model={meta.output_schema_version}, "
                f"runtime={_CURRENT_OUTPUT_SCHEMA_VERSION}",
                context={"model_schema": meta.output_schema_version,
                         "runtime_schema": _CURRENT_OUTPUT_SCHEMA_VERSION},
            )

    def _check_firmware_compatibility(self, meta: ModelMetadata) -> None:
        if not _semver_gte(self._fw_version, meta.min_fw_version):
            raise CompatibilityError(
                f"Firmware {self._fw_version} is below minimum required "
                f"{meta.min_fw_version} for model {meta.model_id} v{meta.version}",
                context={
                    "firmware_version": self._fw_version,
                    "min_fw_version": meta.min_fw_version,
                },
            )

    def _check_feature_compatibility(self, package: DeploymentPackage) -> None:
        required = set(package.compatibility.required_features)
        missing  = required - self._fw_features
        if missing:
            raise CompatibilityError(
                f"Firmware missing required features: {sorted(missing)}",
                context={
                    "required":   sorted(required),
                    "available":  sorted(self._fw_features),
                    "missing":    sorted(missing),
                },
            )
        deprecated = set(package.compatibility.deprecated_features) & self._fw_features
        if deprecated:
            log.warning(
                "validator.deprecated_features_in_use",
                features=sorted(deprecated),
            )

    def _check_model_integrity(self, package: DeploymentPackage) -> None:
        if not package.model_binary:
            raise ValidationError(
                "Model binary is empty",
                context={"package_id": package.package_id},
            )
        if len(package.model_binary) < 64:
            raise ValidationError(
                f"Model binary suspiciously small ({len(package.model_binary)} bytes)",
                context={"size": len(package.model_binary)},
            )


# ── Semver comparison ─────────────────────────────────────────────────────────

def _semver_gte(version: str, minimum: str) -> bool:
    """Return True if *version* >= *minimum* using numeric semver comparison."""
    def parse(v: str) -> tuple[int, ...]:
        try:
            return tuple(int(x) for x in re.split(r"[.\-]", v)[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)
    return parse(version) >= parse(minimum)
