# shared/types/models.py

from dataclasses import dataclass
import struct
from typing import Optional, Any, Dict

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
