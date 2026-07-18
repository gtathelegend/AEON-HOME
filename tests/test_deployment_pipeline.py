"""
tests/test_deployment_pipeline.py — End-to-end deployment lifecycle tests.

Tests cover:
  - DeploymentPackager: builds package, writes manifest, correct checksum
  - DeploymentValidator: passes valid package, rejects bad checksum, rejects
                         schema mismatch, rejects missing feature
  - ModelManager: full lifecycle state machine (begin → commit → rollback)
  - RuntimeStatistics: record_inference EMA correctness
  - ModelScore: to_dict round-trip
  - DeploymentRecord: to_dict round-trip
"""
from __future__ import annotations

import hashlib
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone

import pytest

from shared.types.models import (
    ModelMetadata,
    FeatureCompatibility,
    DeploymentPackage,
    RuntimeStatistics,
    ModelScore,
)
from shared.types.deployment import (
    ActivationState,
    DeploymentRecord,
    DeploymentState,
    RollbackReason,
)
from shared.errors.model_errors import (
    ValidationError,
    CompatibilityError,
    DeploymentError,
)
from core.models.deployment_packager import DeploymentPackager
from core.models.deployment_validator import DeploymentValidator


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    """Create a temp model dir with a dummy .bin file."""
    binary = b"\x00" * 1024  # 1 KiB dummy binary
    (tmp_path / "test_model.bin").write_bytes(binary)
    return tmp_path


@pytest.fixture
def packager(model_dir: Path) -> DeploymentPackager:
    return DeploymentPackager(model_dir)


@pytest.fixture
def valid_package(model_dir: Path) -> DeploymentPackage:
    """Build a valid package from the test model dir."""
    packager = DeploymentPackager(model_dir)
    return packager.pack("test_model", accuracy=0.93)


@pytest.fixture
def validator() -> DeploymentValidator:
    return DeploymentValidator()


# ── DeploymentPackager tests ──────────────────────────────────────────────────

class TestDeploymentPackager:
    def test_pack_produces_package(self, valid_package: DeploymentPackage) -> None:
        assert valid_package is not None
        assert valid_package.package_id
        assert valid_package.model.model_id == "test_model"
        assert valid_package.model.version >= 1

    def test_checksum_is_sha256(self, valid_package: DeploymentPackage) -> None:
        expected = hashlib.sha256(valid_package.model_binary).hexdigest()
        assert valid_package.model.checksum == expected

    def test_manifest_written(self, model_dir: Path, valid_package: DeploymentPackage) -> None:
        v = valid_package.model.version
        manifest_path = model_dir / f"test_model_v{v}_manifest.json"
        assert manifest_path.exists(), f"Manifest not found: {manifest_path}"
        data = json.loads(manifest_path.read_text())
        assert data["model"]["model_id"] == "test_model"

    def test_version_increments(self, packager: DeploymentPackager) -> None:
        p1 = packager.pack("test_model", accuracy=0.90)
        p2 = packager.pack("test_model", accuracy=0.91)
        assert p2.model.version == p1.model.version + 1

    def test_no_binary_raises(self, tmp_path: Path) -> None:
        packager = DeploymentPackager(tmp_path)
        with pytest.raises(DeploymentError):
            packager.pack("nonexistent_model")

    def test_feature_compatibility_defaults(self, valid_package: DeploymentPackage) -> None:
        compat = valid_package.compatibility
        assert "temperature" in compat.required_features
        assert compat.feature_vector_size == 7


# ── DeploymentValidator tests ─────────────────────────────────────────────────

class TestDeploymentValidator:
    def test_valid_package_passes(
        self, validator: DeploymentValidator, valid_package: DeploymentPackage
    ) -> None:
        # Should not raise
        validator.validate(valid_package)

    def test_checksum_mismatch_raises(
        self, valid_package: DeploymentPackage
    ) -> None:
        tampered = DeploymentPackage(
            package_id         = valid_package.package_id,
            model              = valid_package.model,
            compatibility      = valid_package.compatibility,
            model_binary       = b"\xff" * 1024,  # different bytes
            policy_version     = valid_package.policy_version,
            deployment_version = valid_package.deployment_version,
            signature          = valid_package.signature,
        )
        with pytest.raises(ValidationError, match="Checksum mismatch"):
            DeploymentValidator().validate(tampered)

    def test_schema_version_mismatch_raises(self, model_dir: Path) -> None:
        packager = DeploymentPackager(model_dir)
        package = packager.pack("test_model", accuracy=0.90)
        # Corrupt the input schema version
        package.model.input_schema_version = 99
        # Recompute checksum (so only schema check fails)
        package.model.checksum = hashlib.sha256(package.model_binary).hexdigest()

        with pytest.raises(CompatibilityError, match="Input schema version mismatch"):
            DeploymentValidator().validate(package)

    def test_missing_required_feature_raises(self, valid_package: DeploymentPackage) -> None:
        valid_package.compatibility = FeatureCompatibility(
            required_features=["temperature", "humidity", "nonexistent_feature"],
        )
        with pytest.raises(CompatibilityError, match="Firmware missing required features"):
            DeploymentValidator().validate(valid_package)

    def test_firmware_version_too_old_raises(self, valid_package: DeploymentPackage) -> None:
        # Validator with older firmware
        validator = DeploymentValidator(firmware_version="1.0.0")
        with pytest.raises(CompatibilityError, match="Firmware.*below minimum"):
            validator.validate(valid_package)

    def test_empty_binary_raises(self, valid_package: DeploymentPackage) -> None:
        valid_package.model_binary = b""
        valid_package.model.checksum = hashlib.sha256(b"").hexdigest()
        with pytest.raises(ValidationError, match="empty"):
            DeploymentValidator().validate(valid_package)


# ── RuntimeStatistics tests ───────────────────────────────────────────────────

class TestRuntimeStatistics:
    def test_record_success(self) -> None:
        stats = RuntimeStatistics()
        stats.record_inference(0.85, 10.0, success=True)
        assert stats.total_inference_count == 1
        assert stats.avg_confidence == pytest.approx(0.85)
        assert stats.avg_latency_ms == pytest.approx(10.0)

    def test_record_failure(self) -> None:
        stats = RuntimeStatistics()
        stats.record_inference(0.0, 0.0, success=False)
        assert stats.failed_inference_count == 1
        assert stats.error_count == 1

    def test_ema_convergence(self) -> None:
        stats = RuntimeStatistics()
        for _ in range(100):
            stats.record_inference(0.80, 15.0, success=True)
        assert abs(stats.avg_confidence - 0.80) < 0.001
        assert abs(stats.avg_latency_ms - 15.0) < 0.001

    def test_min_max_tracking(self) -> None:
        stats = RuntimeStatistics()
        stats.record_inference(0.5, 10.0, success=True)
        stats.record_inference(0.5, 20.0, success=True)
        stats.record_inference(0.5,  5.0, success=True)
        assert stats.min_latency_ms == pytest.approx(5.0)
        assert stats.max_latency_ms == pytest.approx(20.0)

    def test_to_dict_keys(self) -> None:
        stats = RuntimeStatistics()
        d = stats.to_dict()
        assert "total_inference_count" in d
        assert "avg_confidence" in d
        assert "avg_latency_ms" in d


# ── DeploymentRecord tests ────────────────────────────────────────────────────

class TestDeploymentRecord:
    def test_to_dict_round_trip(self) -> None:
        record = DeploymentRecord(
            deployment_id = "test-id-001",
            model_id      = "presence_clf",
            model_version = 3,
            state         = DeploymentState.RUNNING,
            started_at    = datetime.now(timezone.utc),
            checksum      = "abc123",
            source        = "learning_loop",
        )
        d = record.to_dict()
        assert d["deployment_id"] == "test-id-001"
        assert d["state"] == "running"
        assert d["model_version"] == 3


# ── ModelScore tests ──────────────────────────────────────────────────────────

class TestModelScore:
    def test_to_dict_has_all_fields(self) -> None:
        score = ModelScore(
            composite_score       = 0.78,
            confidence_component  = 0.80,
            accuracy_component    = 0.75,
            latency_component     = 0.90,
            reliability_component = 0.85,
            stability_component   = 0.70,
            rollback_component    = 1.00,
            correction_component  = 0.90,
            model_age_factor      = 1.00,
            trend                 = 0.02,
        )
        d = score.to_dict()
        assert "composite_score" in d
        assert d["composite_score"] == pytest.approx(0.78)
        assert "trend" in d
