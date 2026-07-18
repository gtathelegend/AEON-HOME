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
    gate: str = "abstain"          # act | ask | abstain
    online: bool = True            # leaf reachable
    changed_at: float = 0.0

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
            "confidence": round(self.confidence, 2),
            "gate": self.gate,
            "online": self.online,
            "learned_from": d.learned_from,
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


class HubState:
    """Everything both dashboards render, in one place."""

    LOG_CAP = 60

    def __init__(self) -> None:
        self.devices: dict[str, DeviceState] = {
            d: DeviceState(id=d) for d in devices.DEVICE_ORDER
        }
        self.policy = Policy()
        self.log: deque[dict] = deque(maxlen=self.LOG_CAP)

        # node health
        self.node_online = False
        self.ckpt_seq = 0
        self.restore_ms = 0.0
        self.link = "down"           # connected | down | reconnecting
        self.pc_reachable = True

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
            },
            "ambient": {
                "temp_c": round(self.temp_c, 1),
                "rh_pct": round(self.rh_pct, 1),
                "motion": self.motion,
                "occupied": self.occupied,
            },
            "devices": [self.devices[d].snapshot() for d in devices.DEVICE_ORDER],
            "policy": self.policy.snapshot(),
            "learned_week": self.learned_week,
            "egress": {
                "cloud_bytes": self.cloud_bytes,
                "local_packets": self.local_packets,
                "spooled": self.spooled,
            },
            "log": list(self.log),
        }
