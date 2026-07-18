# shared/events/__init__.py

from dataclasses import dataclass
from typing import Any, Dict

# Event Names
PREFERENCE_RECEIVED = "PreferenceReceived"
PREFERENCE_UPDATED = "PreferenceUpdated"
TELEMETRY_RECEIVED = "TelemetryReceived"
MODEL_TRAINED = "ModelTrained"
MODEL_DEPLOYED = "ModelDeployed"
CHECKPOINT_SAVED = "CheckpointSaved"
CHECKPOINT_LOADED = "CheckpointLoaded"
INFERENCE_COMPLETED = "InferenceCompleted"
DEVICE_UPDATED = "DeviceUpdated"


@dataclass
class PreferenceReceived:
    user_id: str
    setting: str
    value: Any


@dataclass
class PreferenceUpdated:
    user_id: str
    setting: str
    value: Any


@dataclass
class TelemetryReceived:
    device_id: str
    payload: Dict[str, Any]


@dataclass
class ModelTrained:
    model_name: str
    version: str
    accuracy: float


@dataclass
class ModelDeployed:
    model_name: str
    version: str


@dataclass
class CheckpointSaved:
    device_id: str
    checkpoint_id: int


@dataclass
class CheckpointLoaded:
    device_id: str
    checkpoint_id: int


@dataclass
class InferenceCompleted:
    model_name: str
    latency_ms: float
    output: Dict[str, Any]


@dataclass
class DeviceUpdated:
    device_id: str
    status: str
