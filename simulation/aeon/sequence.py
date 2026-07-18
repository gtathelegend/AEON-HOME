"""The 24-step lag window: history -> model input.

A per-hour lookup table cannot express "the AC comes on at 09:00 because it was
off overnight and someone just got up", or "an override an hour ago should still
be respected". Those depend on recent history, not on the clock alone.

So the model reads a full day of what the home has been doing, plus where we are
in the week, plus which appliance is being asked about:

    window   24 steps x 4 channels   =  96
    context  hour_sin/cos, dow_sin/cos, is_weekend, ambient_z   =   6
    device one-hot                                              =   4
                                                        input   = 106
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import devices

WINDOW = 24              # steps of history the model sees
CHANNELS = 4             # device_on, level, occupancy, ambient
CONTEXT = 6              # hour sin/cos, dow sin/cos, is_weekend, ambient z
STEP_SECONDS = 3600.0    # one step is one hour

INPUT_DIM = WINDOW * CHANNELS + CONTEXT + len(devices.DEVICE_ORDER)   # 106


class AlignmentError(Exception):
    """The window is not time-aligned with the step being predicted."""


@dataclass
class Step:
    """One hour of one device's history."""
    on: bool
    level: float | None      # None when off -- see the note in SequenceBuffer.push
    occupied: bool
    ambient_c: float
    ts: float = 0.0


class SequenceBuffer:
    """A rolling 24-step window for ONE device."""

    def __init__(self, device_id: str, steps: list[Step] | None = None) -> None:
        self.device_id = device_id
        self.spec = devices.get(device_id)
        self.steps: list[Step] = list(steps or [])
        self._trim()

    def _trim(self) -> None:
        if len(self.steps) > WINDOW:
            self.steps = self.steps[-WINDOW:]

    @property
    def warm(self) -> bool:
        """True once a full day of real history exists.

        A freshly deployed node has a zero-padded window: the model is being
        asked about a day that never happened, and it can still look decisive.
        """
        return len(self.steps) >= WINDOW

    def push(self, step: Step) -> None:
        """Append the applied state.

        `level` must be None when the device is off. Recording the model's raw
        level output for an off step poisons the window and drives the input
        off-distribution within a day -- silently, because every individual
        value still looks plausible.
        """
        if not step.on and step.level is not None:
            step = Step(step.on, None, step.occupied, step.ambient_c, step.ts)
        self.steps.append(step)
        self._trim()

    # -- feature construction ---------------------------------------------

    def flat(self) -> list[float]:
        """The 96 window values only.

        Never feed this to the model directly -- use model_input(). On its own
        it is a dimension error at best and a silently wrong prediction at worst.
        """
        padding = WINDOW - len(self.steps)
        out: list[float] = [0.0] * (padding * CHANNELS)
        for step in self.steps:
            out.append(1.0 if step.on else 0.0)
            # Off steps carry a neutral level; channel 0 is what says "off".
            out.append(self.spec.normalise(step.level) if (step.on and step.level is not None) else 0.0)
            out.append(1.0 if step.occupied else 0.0)
            out.append((step.ambient_c - 28.0) / 8.0)
        return out

    def model_input(
        self,
        now_ts: float,
        ambient_c: float,
        ambient_mean: float = 28.0,
        ambient_std: float = 8.0,
    ) -> np.ndarray:
        """The full 106-value input, shaped [1, 106] for ONNX Runtime."""
        window = self.flat()
        if len(window) != WINDOW * CHANNELS:
            raise ValueError(
                f"window is {len(window)} values, expected {WINDOW * CHANNELS}"
            )

        vector = window + context_features(now_ts, ambient_c, ambient_mean, ambient_std)
        vector += devices.one_hot(self.device_id)

        if len(vector) != INPUT_DIM:
            raise ValueError(f"model input is {len(vector)} values, expected {INPUT_DIM}")
        return np.asarray([vector], dtype=np.float32)

    def check_alignment(self, target_ts: float) -> None:
        """window[-1] must be the step immediately before `target_ts`.

        Raises rather than warns. A missed tick, a bad seed or a stale checkpoint
        silently shifts the whole day, and the model then answers confidently
        about the wrong hour -- a failure that is invisible from the outputs.
        """
        if not self.steps:
            return
        last = self.steps[-1].ts
        if last <= 0:
            return
        gap = target_ts - last
        if not (0 < gap <= STEP_SECONDS * 1.5):
            raise AlignmentError(
                f"{self.device_id}: last window step is {gap / 3600:.2f} h before the "
                f"target, expected about 1 h"
            )

    # -- persistence -------------------------------------------------------

    def to_state(self) -> list[list]:
        """~1.1 KB on eMMC. Without it a restart leaves the model blind to
        recent history until a full day rebuilds."""
        return [[s.on, s.level, s.occupied, s.ambient_c, s.ts] for s in self.steps]

    @classmethod
    def from_state(cls, device_id: str, state: list | None) -> "SequenceBuffer":
        steps = []
        for row in state or []:
            try:
                steps.append(Step(bool(row[0]), row[1], bool(row[2]),
                                  float(row[3]), float(row[4]) if len(row) > 4 else 0.0))
            except (TypeError, IndexError, ValueError):
                continue          # a malformed row is dropped, not fatal
        return cls(device_id, steps)


def context_features(
    now_ts: float,
    ambient_c: float,
    ambient_mean: float = 28.0,
    ambient_std: float = 8.0,
) -> list[float]:
    """Where we are in the week, and how hot it is relative to training.

    Hour and day-of-week are encoded as sin/cos pairs so that 23:00 sits next to
    00:00 instead of at the opposite end of the range.
    """
    import time as _time

    lt = _time.localtime(now_ts)
    hour = lt.tm_hour + lt.tm_min / 60.0
    dow = lt.tm_wday

    std = ambient_std if ambient_std > 1e-6 else 1.0
    return [
        math.sin(2 * math.pi * hour / 24.0),
        math.cos(2 * math.pi * hour / 24.0),
        math.sin(2 * math.pi * dow / 7.0),
        math.cos(2 * math.pi * dow / 7.0),
        1.0 if dow >= 5 else 0.0,
        (ambient_c - ambient_mean) / std,
    ]


def build_windows(
    device_id: str,
    timeline: list[Step],
    ambient_mean: float = 28.0,
    ambient_std: float = 8.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A device's hourly timeline -> (X, y_on, y_level).

    Window i predicts step i, so the window is timeline[i-WINDOW:i] and never
    includes the step being predicted. Off-by-one here is the alignment bug that
    check_alignment() exists to catch at runtime.

    y_level is only meaningful where y_on is 1; callers mask on that.
    """
    X: list[list[float]] = []
    y_on: list[float] = []
    y_level: list[float] = []

    spec = devices.get(device_id)
    one_hot = devices.one_hot(device_id)

    for i in range(WINDOW, len(timeline)):
        history = timeline[i - WINDOW:i]
        target = timeline[i]

        buffer = SequenceBuffer(device_id, history)
        vector = buffer.flat()
        vector += context_features(target.ts, target.ambient_c, ambient_mean, ambient_std)
        vector += one_hot

        X.append(vector)
        y_on.append(1.0 if target.on else 0.0)
        y_level.append(
            spec.normalise(target.level) if (target.on and target.level is not None) else 0.0
        )

    if not X:
        empty = np.zeros((0, INPUT_DIM), dtype=np.float32)
        return empty, np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)

    return (
        np.asarray(X, dtype=np.float32),
        np.asarray(y_on, dtype=np.float32),
        np.asarray(y_level, dtype=np.float32),
    )
