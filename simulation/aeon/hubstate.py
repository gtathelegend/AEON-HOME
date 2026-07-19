"""The single state object every screen renders from.

Phase 1 drives this from a scripted demo source. Phase 2 drives the same object
from the real central node and SQLite. The dashboard never learns which, because
`snapshot()` is the only thing it ever sees -- that is the seam that lets the
backend land underneath a finished UI without touching the UI.

Preferences live only on the PC; phone and PC dashboards both read this over
WebSocket, so they cannot disagree.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from . import devices


@dataclass
class DeviceState:
    id: str
    on: bool = False
    level: float | None = None
    source: str = "idle"           # phone | model | manual | idle
    confidence: float = 0.0
    gate: str = "abstain"          # act | ask | abstain | held
    online: bool = True            # leaf reachable
    changed_at: float = 0.0
    # What the model wanted this tick, which is only interesting when it differs
    # from what the appliance is doing -- i.e. when the gate withheld the action.
    want_on: bool = False
    want_level: float | None = None

    def snapshot(self) -> dict:
        d = devices.get(self.id)
        return {
            "id": self.id,
            "label": d.label,
            "on": self.on,
            "level": self.level,
            "level_text": d.format_level(self.level if self.on else None),
            "level_name": d.level_name,
            "unit": d.unit,
            "range": [d.lo, d.hi],
            "source": self.source,
            # Four decimals, not two. Confidence is 0.65*|p_on-0.5|*2 + 0.35, so a
            # decisive model lives around 0.998 and moves in the third decimal as
            # the hour and the lag window change. Rounding to 2 dp flattened all
            # of that to a motionless "1.00", which reads as a hardcoded label
            # rather than a live model output.
            "confidence": round(self.confidence, 4),
            "gate": self.gate,
            "online": self.online,
            "learned_from": d.learned_from,
            # Only populated into a question when the gate held the action back;
            # the phone decides whether it is worth asking about.
            "want_on": self.want_on,
            "want_level": self.want_level,
            "want_text": d.format_level(self.want_level if self.want_on else None),
        }


@dataclass
class Policy:
    model_v: int = 0
    cv_auc: float | None = None
    level_mae: dict[str, float] = field(default_factory=dict)
    n_windows: int = 0
    params: int = 0
    size_bytes: int = 0
    sha256: str = ""
    train_seconds: float = 0.0
    trained_at: float = 0.0
    # What the artefact actually is. Phase 2 ships a compiled schedule; Phase 3
    # ships an int8 ONNX model. Labelling a JSON blob "int8" would be a claim
    # about the system that happens not to be true yet.
    kind: str = "schedule"

    def snapshot(self) -> dict:
        return {
            "model_v": self.model_v,
            "cv_auc": self.cv_auc,
            "level_mae": {
                k: {"value": v, "text": devices.get(k).format_error(v)}
                for k, v in self.level_mae.items()
            },
            "n_windows": self.n_windows,
            "params": self.params,
            "size_bytes": self.size_bytes,
            "kind": self.kind,
            "sha256": self.sha256[:16],
            "train_seconds": round(self.train_seconds, 2),
            "trained_at": self.trained_at,
        }


@dataclass
class Candidate:
    """A model that has been trained but NOT deployed.

    Retrain and Redeploy are two buttons because they are two decisions. Training
    produces a candidate and a verdict; deploying acts on that verdict. Holding
    the artefact here in between is what lets the screen say "this one is better
    than what is running" before anything reaches the node -- and what lets
    Redeploy stay disabled when it is not.
    """
    exists: bool = False
    better: bool = False
    reason: str = ""
    cv_auc: float | None = None
    incumbent_auc: float | None = None
    n_windows: int = 0
    stated_windows: int = 0
    observed_windows: int = 0
    observed_hours: int = 0
    level_mae: dict[str, float] = field(default_factory=dict)
    incumbent_mae: dict[str, float] = field(default_factory=dict)
    size_bytes: int = 0
    train_seconds: float = 0.0
    trained_at: float = 0.0

    def snapshot(self) -> dict:
        return {
            "exists": self.exists,
            "better": self.better,
            "reason": self.reason,
            "cv_auc": self.cv_auc,
            "incumbent_auc": self.incumbent_auc,
            "n_windows": self.n_windows,
            "stated_windows": self.stated_windows,
            "observed_windows": self.observed_windows,
            "observed_hours": self.observed_hours,
            "level_mae": {
                k: {
                    "value": v,
                    "text": devices.get(k).format_error(v),
                    "was": self.incumbent_mae.get(k),
                    "was_text": (devices.get(k).format_error(self.incumbent_mae[k])
                                 if k in self.incumbent_mae else None),
                }
                for k, v in self.level_mae.items()
            },
            "size_bytes": self.size_bytes,
            "train_seconds": round(self.train_seconds, 2),
            "trained_at": self.trained_at,
        }


@dataclass
class AIHubState:
    """Qualcomm AI Hub compile + profile, reported as it happens.

    Held separately from the policy because it is slow and optional. A profile
    job took 365 s against a 2 s training run, so it cannot sit inside the
    button press: the screen would freeze for six minutes in the middle of a
    five-minute demo. It runs in the background and this fills in when it lands.
    """
    state: str = "idle"          # idle | running | done | failed | unavailable
    device: str = ""
    inference_us: float | None = None
    peak_memory_mb: float | None = None
    compute_unit: str = ""
    compile_job: str = ""
    profile_job: str = ""
    artefact_bytes: int = 0
    elapsed_s: float = 0.0
    reason: str = ""
    local_us: float | None = None

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "device": self.device,
            "inference_us": self.inference_us,
            "peak_memory_mb": self.peak_memory_mb,
            "compute_unit": self.compute_unit,
            "compile_job": self.compile_job,
            "profile_job": self.profile_job,
            "artefact_bytes": self.artefact_bytes,
            "elapsed_s": round(self.elapsed_s, 1),
            "reason": self.reason,
            "local_us": self.local_us,
        }


class HubState:
    """Everything both dashboards render, in one place."""

    LOG_CAP = 60

    def __init__(self) -> None:
        self.devices: dict[str, DeviceState] = {
            d: DeviceState(id=d) for d in devices.DEVICE_ORDER
        }
        self.policy = Policy()
        self.candidate = Candidate()
        self.aihub = AIHubState()
        self.log: deque[dict] = deque(maxlen=self.LOG_CAP)

        # node health
        self.node_online = False
        self.ckpt_seq = 0
        self.restore_ms = 0.0
        self.link = "down"           # connected | down | reconnecting
        self.pc_reachable = True
        # Is the model allowed to act on its own? False means the house does
        # exactly what it is told and nothing else.
        self.automation = True
        # How many phones are attached. Set by the server as sockets come and go.
        self.phones = 0

        # ambient, read by the central node for the whole zone
        self.temp_c = 28.0
        self.rh_pct = 55.0
        self.motion = 0
        self.occupied = False

        # the egress ledger. cloud_bytes is the headline number and it is zero.
        self.cloud_bytes = 0
        self.local_packets = 0
        self.spooled = 0

        # demo clock -- the wall clock the house believes it is
        self.clock_ts = time.time()

        self.learned_week: list[dict] = []

    # -- mutation ---------------------------------------------------------

    def event(self, kind: str, **fields) -> dict:
        """Append to the live log. Returns the event so callers can also push it."""
        ev = {"typ": "event", "kind": kind, "ts": time.time(), **fields}
        self.log.appendleft(ev)
        return ev

    def apply_leaf_ack(self, device: str, on: bool, level: float | None,
                       source: str, confidence: float = 0.0, gate: str = "act") -> None:
        ds = self.devices[device]
        ds.on = on
        ds.level = level
        ds.source = source
        ds.confidence = confidence
        ds.gate = gate
        ds.changed_at = time.time()

    # -- read -------------------------------------------------------------

    def snapshot(self) -> dict:
        lt = time.localtime(self.clock_ts)
        return {
            "typ": "state",
            "ts": time.time(),
            "clock": time.strftime("%H:%M", lt),
            "clock_day": time.strftime("%a", lt).upper(),
            "node": {
                "online": self.node_online,
                "model_v": self.policy.model_v,
                "ckpt_seq": self.ckpt_seq,
                "restore_ms": round(self.restore_ms, 1),
                "link": self.link,
                "pc_reachable": self.pc_reachable,
                "automation": self.automation,
                "phones": self.phones,
            },
            "ambient": {
                "temp_c": round(self.temp_c, 1),
                "rh_pct": round(self.rh_pct, 1),
                "motion": self.motion,
                "occupied": self.occupied,
            },
            "devices": [self.devices[d].snapshot() for d in devices.DEVICE_ORDER],
            "policy": self.policy.snapshot(),
            "candidate": self.candidate.snapshot(),
            "aihub": self.aihub.snapshot(),
            "learned_week": self.learned_week,
            "egress": {
                "cloud_bytes": self.cloud_bytes,
                "local_packets": self.local_packets,
                "spooled": self.spooled,
            },
            "log": list(self.log),
        }
