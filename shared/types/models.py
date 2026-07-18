# shared/types/models.py

from dataclasses import dataclass, field
import struct
from typing import Optional, Any, Dict, List


@dataclass
class FeatureFrame:
    temperature:   float
    humidity:      float
    motion:        bool
    door_open:     bool
    mean_temp:     float
    var_temp:      float
    delta_motion:  float
    timestamp_ms:  int
    seq:           int

    # Struct layout must match Arduino FeatureFrame exactly (little-endian)
    _STRUCT = struct.Struct("<ffBBfffI")

    @classmethod
    def from_bytes(cls, data: bytes, seq: int) -> "FeatureFrame":
        t, h, m, d, mt, vt, dm, ts = cls._STRUCT.unpack_from(data)
        return cls(
            temperature=t, humidity=h,
            motion=bool(m), door_open=bool(d),
            mean_temp=mt, var_temp=vt,
            delta_motion=dm, timestamp_ms=ts,
            seq=seq,
        )

    @classmethod
    def from_json(cls, data: dict) -> "FeatureFrame":
        return cls(
            temperature=float(data.get("temp", 0.0)),
            humidity=float(data.get("humidity", 0.0)),
            motion=bool(data.get("motion", False)),
            door_open=bool(data.get("door", False)),
            mean_temp=float(data.get("mean_t", 0.0)),
            var_temp=float(data.get("var_t", 0.0)),
            delta_motion=float(data.get("d_motion", 0.0)),
            timestamp_ms=int(data.get("ts", 0)),
            seq=int(data.get("seq", 0)),
        )


@dataclass
class AeonEvent:
    category: str
    name:     str
    arg:      int
    seq:      int

    @classmethod
    def from_json(cls, data: dict) -> "AeonEvent":
        typ = data.get("typ", "unknown")

        category = "feedback"
        name = "unknown"
        arg = 0

        if typ == "feedback_event":
            category = "feedback"
            name = data.get("event", "unknown")
            arg = data.get("arg", 1)
        elif typ == "memory_status":
            category = "memory"
            name = "usage"
            arg = data.get("pct", 0)
        elif typ == "model_ack":
            category = "model"
            name = "ack"
            arg = data.get("model_v", 0)
        elif typ == "policy_ack":
            category = "policy"
            name = "ack"
            arg = 0

        return cls(
            category=category,
            name=name,
            arg=int(arg),
            seq=int(data.get("seq", 0)),
        )


@dataclass
class PolicyDecision:
    action:     str          # e.g. "notify", "actuate_relay", "no_action"
    confidence: float        # 0.0–1.0
    reason:     str
    frame_seq:  int
    token_id:   str | None = None   # set by auth module when token is issued
    latency_ms: float = 0.0         # NPU inference latency


@dataclass
class DeviceInfo:
    id:     str
    type:   str
    status: str
    meta:   Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# Model Lifecycle Types (added in Commit 3)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModelMetadata:
    """Full metadata for a deployed model instance."""
    model_id:              str
    version:               int
    training_timestamp:    str          # ISO-8601
    dataset_version:       str
    feature_version:       str
    deployment_timestamp:  str          # ISO-8601
    deployment_source:     str          # e.g. "learning_loop", "manual_upload"
    input_schema_version:  int
    output_schema_version: int
    supported_fw_version:  str          # e.g. "2.0.0"
    min_fw_version:        str          # minimum compatible firmware
    compatibility_version: int
    checksum:              str          # SHA-256 hex of model binary
    activation_state:      str          # ActivationState value
    # Runtime metrics (updated post-deployment)
    accuracy_estimate:     float = 0.0
    historical_accuracy:   List[float] = field(default_factory=list)
    avg_confidence:        float = 0.0
    avg_latency_ms:        float = 0.0
    inference_count:       int   = 0
    last_updated:          Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "model_id":              self.model_id,
            "version":               self.version,
            "training_timestamp":    self.training_timestamp,
            "dataset_version":       self.dataset_version,
            "feature_version":       self.feature_version,
            "deployment_timestamp":  self.deployment_timestamp,
            "deployment_source":     self.deployment_source,
            "input_schema_version":  self.input_schema_version,
            "output_schema_version": self.output_schema_version,
            "supported_fw_version":  self.supported_fw_version,
            "min_fw_version":        self.min_fw_version,
            "compatibility_version": self.compatibility_version,
            "checksum":              self.checksum,
            "activation_state":      self.activation_state,
            "accuracy_estimate":     self.accuracy_estimate,
            "historical_accuracy":   self.historical_accuracy,
            "avg_confidence":        self.avg_confidence,
            "avg_latency_ms":        self.avg_latency_ms,
            "inference_count":       self.inference_count,
            "last_updated":          self.last_updated,
        }


@dataclass
class FeatureCompatibility:
    """Declares what features a model requires, accepts, and rejects."""
    required_features:    List[str]
    optional_features:    List[str] = field(default_factory=list)
    deprecated_features:  List[str] = field(default_factory=list)
    feature_vector_size:  int = 7      # must match firmware FEATURE_VECTOR_LEN


@dataclass
class DeploymentPackage:
    """
    Self-contained deployment unit sent from Snapdragon to the firmware.

    Contains the model binary (as bytes or a file path reference),
    full metadata, compatibility info, and integrity checksums.
    """
    package_id:        str
    model:             ModelMetadata
    compatibility:     FeatureCompatibility
    model_binary:      bytes               # raw model weights / ONNX bytes
    policy_version:    int
    deployment_version: int
    signature:         str                 # HMAC-SHA256 stub (future use)

    def to_manifest_dict(self) -> dict:
        """Serializable manifest (no binary blob)."""
        return {
            "package_id":         self.package_id,
            "model":              self.model.to_dict(),
            "compatibility":      {
                "required_features":   self.compatibility.required_features,
                "optional_features":   self.compatibility.optional_features,
                "deprecated_features": self.compatibility.deprecated_features,
                "feature_vector_size": self.compatibility.feature_vector_size,
            },
            "policy_version":     self.policy_version,
            "deployment_version": self.deployment_version,
            "signature":          self.signature,
        }


@dataclass
class RuntimeStatistics:
    """
    Persistent runtime statistics for the active model.
    These survive reboots via AeonState flash persistence.
    """
    total_inference_count: int   = 0
    avg_confidence:        float = 0.0
    avg_latency_ms:        float = 0.0
    min_latency_ms:        float = float("inf")
    max_latency_ms:        float = 0.0
    error_count:           int   = 0
    failed_inference_count: int  = 0
    invalid_input_count:   int   = 0
    model_uptime_s:        float = 0.0
    runtime_resets:        int   = 0

    def record_inference(self, confidence: float, latency_ms: float, success: bool) -> None:
        self.total_inference_count += 1
        if success:
            n = self.total_inference_count
            self.avg_confidence = self.avg_confidence + (confidence - self.avg_confidence) / n
            self.avg_latency_ms = self.avg_latency_ms + (latency_ms - self.avg_latency_ms) / n
            self.min_latency_ms = min(self.min_latency_ms, latency_ms)
            self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        else:
            self.failed_inference_count += 1
            self.error_count += 1

    def to_dict(self) -> dict:
        return {
            "total_inference_count":  self.total_inference_count,
            "avg_confidence":         self.avg_confidence,
            "avg_latency_ms":         self.avg_latency_ms,
            "min_latency_ms":         self.min_latency_ms if self.min_latency_ms != float("inf") else 0.0,
            "max_latency_ms":         self.max_latency_ms,
            "error_count":            self.error_count,
            "failed_inference_count": self.failed_inference_count,
            "invalid_input_count":    self.invalid_input_count,
            "model_uptime_s":         self.model_uptime_s,
            "runtime_resets":         self.runtime_resets,
        }


@dataclass
class ScoreWeights:
    """
    Configurable weights for composite model scoring.
    All weights should sum to 1.0.
    """
    confidence:       float = 0.25
    accuracy:         float = 0.20
    correction_rate:  float = 0.15  # lower is better (inverted in scorer)
    latency:          float = 0.10  # lower is better (inverted in scorer)
    reliability:      float = 0.15
    rollback_history: float = 0.10  # lower rollbacks is better (inverted)
    stability:        float = 0.05


@dataclass
class ModelScore:
    """Composite normalized model quality score (0.0–1.0)."""
    composite_score:     float          # final normalized score
    confidence_component: float
    accuracy_component:  float
    latency_component:   float
    reliability_component: float
    stability_component: float
    rollback_component:  float
    correction_component: float
    model_age_factor:    float          # 1.0 = fresh, decreases over time
    trend:               float          # +/- recent performance delta
    computed_at:         Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "composite_score":       self.composite_score,
            "confidence_component":  self.confidence_component,
            "accuracy_component":    self.accuracy_component,
            "latency_component":     self.latency_component,
            "reliability_component": self.reliability_component,
            "stability_component":   self.stability_component,
            "rollback_component":    self.rollback_component,
            "correction_component":  self.correction_component,
            "model_age_factor":      self.model_age_factor,
            "trend":                 self.trend,
            "computed_at":           self.computed_at,
        }


class ConfidenceCategory(str):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_value(cls, v: float) -> str:
        if v < 0.40:
            return cls.LOW
        if v < 0.65:
            return cls.MEDIUM
        if v < 0.85:
            return cls.HIGH
        return cls.CRITICAL


@dataclass
class ConfidenceReport:
    """
    Full confidence breakdown from the ConfidenceEngine.
    Consumed by the policy engine and telemetry pipeline.
    """
    raw_confidence:        float
    stability_adjustment:  float        # rolling variance penalty
    runtime_adjustment:    float        # penalize high error rate
    historical_adjustment: float        # compared to historical baseline
    context_adjustment:    float        # time-of-day / occupancy context
    final_confidence:      float
    confidence_category:   str          # ConfidenceCategory value
    reason:                str
    explanation:           str

    def to_dict(self) -> dict:
        return {
            "raw_confidence":        self.raw_confidence,
            "stability_adjustment":  self.stability_adjustment,
            "runtime_adjustment":    self.runtime_adjustment,
            "historical_adjustment": self.historical_adjustment,
            "context_adjustment":    self.context_adjustment,
            "final_confidence":      self.final_confidence,
            "confidence_category":   self.confidence_category,
            "reason":                self.reason,
            "explanation":           self.explanation,
        }

