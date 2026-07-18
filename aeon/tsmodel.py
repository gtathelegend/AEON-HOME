"""Train on the AI PC, export ONNX, quantise to int8, deploy to the node.

Architecture -- two heads, because "should it be on?" and "at what setting?" are
different questions:

    input (105) -> Dense(32) + tanh -> Dense(1) + sigmoid -> p_on
                -> Dense(32) + tanh -> Dense(1)           -> level

6,850 parameters: 2 x (105*32 + 32 + 32 + 1).

Why this and not an LSTM/GRU. It sees the same 24-step history, trains in
seconds without a deep-learning runtime, exports to a few KB of ONNX, and runs
in microseconds on the node -- where a recurrent model's sequential unroll costs
far more for no measurable gain on a 24-step window. If the window later needs
hundreds of steps that trade flips and a recurrent model earns its place.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import devices, sequence
from .sequence import Step

HIDDEN = 32
DAYS_OF_SYNTHESIS = 28

# Guardrails (§4.11)
MIN_WINDOWS = 200
MIN_CV_AUC = 0.60

# Cross-validation is a gate, not a deliverable -- see _cross_val_auc.
CV_FOLDS = 3
CV_MAX_ITER = 400


@dataclass
class TrainResult:
    ok: bool
    reason: str = ""
    n_windows: int = 0
    params: int = 0
    cv_auc: float | None = None
    level_mae: dict[str, float] = field(default_factory=dict)
    train_seconds: float = 0.0
    iterations: int = 0
    onnx_fp32: bytes = b""
    onnx_int8: bytes = b""
    sha256: str = ""
    warm_start: dict[str, list] = field(default_factory=dict)
    ambient_mean: float = 28.0
    ambient_std: float = 8.0


# ── synthesising a timeline from stated preferences ──────────────────────

def ambient_for_hour(hour: int) -> float:
    """The same daily curve the simulator uses, so training and runtime agree."""
    return 26.0 + 7.0 * math.cos((hour - 15.0) / 24.0 * 2 * math.pi)


def synthesise(device_id: str, active_rows, days: int = DAYS_OF_SYNTHESIS,
               start_ts: float | None = None) -> list[Step]:
    """A stated preference is not one data point -- it describes every day.

    So it is expanded into a coherent timeline: `days` x 24 hourly steps, where
    commanded hours follow the command and the rest default to off.

    One row per timestep, never duplicated. The obvious way to weight a stated
    preference is to repeat its row N times; that is fine for tabular data and
    catastrophic for a sequence model, because the 24-step lag window then fills
    with N identical copies of the same hour instead of a plausible day, and the
    model trains on histories that cannot physically occur.
    """
    rows = [r for r in active_rows if r["device"] == device_id]
    base = start_ts if start_ts is not None else time.time() - days * 86400

    # Snap to midnight so day-of-week features line up with real days.
    lt = time.localtime(base)
    midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))

    timeline: list[Step] = []
    for day in range(days):
        for hour in range(24):
            ts = midnight + (day * 24 + hour) * 3600
            weekday = time.localtime(ts).tm_wday
            is_weekend = weekday >= 5

            on, level = False, None
            for row in rows:
                if not _covers(row, hour, is_weekend):
                    continue
                on = bool(row["on_state"])
                level = row["level"] if on else None

            occupied = devices.default_occupancy(hour)
            # Occupancy overrides the preference in training exactly as it does
            # at runtime; a model taught otherwise fights the runtime override.
            if not occupied and devices.get(device_id).off_when_empty:
                on, level = False, None

            timeline.append(Step(on, level, occupied, ambient_for_hour(hour), ts))

    return timeline


def _covers(row, hour: int, is_weekend: bool) -> bool:
    day_type = row["day_type"]
    if day_type == "weekday" and is_weekend:
        return False
    if day_type == "weekend" and not is_weekend:
        return False
    start, end = row["hour_start"], row["hour_end"]
    return start <= hour < end


# ── the network ──────────────────────────────────────────────────────────

def _train_head(X: np.ndarray, y: np.ndarray, classifier: bool, seed: int = 0):
    """One 105 -> 32 -> 1 head.

    Trains to convergence, not to an iteration ceiling. An earlier build capped
    at 400 iterations, hit the ceiling every time, and produced an under-trained
    model that still scored acceptably.
    """
    from sklearn.neural_network import MLPClassifier, MLPRegressor

    common = dict(
        hidden_layer_sizes=(HIDDEN,),
        activation="tanh",
        solver="adam",
        max_iter=3000,
        tol=1e-5,
        n_iter_no_change=25,
        random_state=seed,
    )
    model = MLPClassifier(**common) if classifier else MLPRegressor(**common)
    model.fit(X, y)
    return model


def count_params() -> int:
    per_head = sequence.INPUT_DIM * HIDDEN + HIDDEN + HIDDEN + 1
    return 2 * per_head


# ── ONNX export ──────────────────────────────────────────────────────────

def _export_onnx(clf, reg) -> bytes:
    """Hand-build the graph from the fitted weights.

    Built directly rather than via skl2onnx: this is two small MLPs and the
    graph is a dozen nodes, so constructing it here keeps the exact two-output
    contract the node depends on and removes a converter from the dependency
    list.
    """
    from onnx import TensorProto, helper, numpy_helper

    def head(prefix: str, model, sigmoid: bool):
        w1 = model.coefs_[0].astype(np.float32)          # [105, 32]
        b1 = model.intercepts_[0].astype(np.float32)     # [32]
        w2 = model.coefs_[1].astype(np.float32)          # [32, 1]
        b2 = model.intercepts_[1].astype(np.float32)     # [1]

        inits = [
            numpy_helper.from_array(w1, f"{prefix}_w1"),
            numpy_helper.from_array(b1, f"{prefix}_b1"),
            numpy_helper.from_array(w2, f"{prefix}_w2"),
            numpy_helper.from_array(b2, f"{prefix}_b2"),
        ]
        nodes = [
            helper.make_node("MatMul", ["input", f"{prefix}_w1"], [f"{prefix}_mm1"]),
            helper.make_node("Add", [f"{prefix}_mm1", f"{prefix}_b1"], [f"{prefix}_a1"]),
            helper.make_node("Tanh", [f"{prefix}_a1"], [f"{prefix}_h"]),
            helper.make_node("MatMul", [f"{prefix}_h", f"{prefix}_w2"], [f"{prefix}_mm2"]),
            helper.make_node("Add", [f"{prefix}_mm2", f"{prefix}_b2"],
                             [f"{prefix}_out_raw" if sigmoid else prefix]),
        ]
        if sigmoid:
            nodes.append(helper.make_node("Sigmoid", [f"{prefix}_out_raw"], [prefix]))
        return nodes, inits

    on_nodes, on_inits = head("p_on", clf, sigmoid=True)
    lv_nodes, lv_inits = head("level", reg, sigmoid=False)

    graph = helper.make_graph(
        nodes=on_nodes + lv_nodes,
        name="aeon_ts",
        inputs=[helper.make_tensor_value_info(
            "input", TensorProto.FLOAT, [None, sequence.INPUT_DIM])],
        outputs=[
            helper.make_tensor_value_info("p_on", TensorProto.FLOAT, [None, 1]),
            helper.make_tensor_value_info("level", TensorProto.FLOAT, [None, 1]),
        ],
        initializer=on_inits + lv_inits,
    )

    model = helper.make_model(
        graph,
        producer_name="aeon-home",
        opset_imports=[helper.make_opsetid("", 13)],
    )
    model.ir_version = 8        # ORT-compatible; the default tracks onnx, not ORT
    return model.SerializeToString()


def warm_up() -> float:
    """Pay the quantiser's import cost at boot instead of at demo time.

    The first call to quantize_dynamic takes ~8.5 s and every later one ~0.2 s:
    that is onnxruntime.quantization loading, not work on our 28 KB model.
    Importing it during startup moves the whole cost off the path of the person
    pressing Retrain.
    """
    t0 = time.perf_counter()
    try:
        from onnxruntime.quantization import quantize_dynamic  # noqa: F401
    except Exception:
        return 0.0
    return time.perf_counter() - t0


def quantise_int8(fp32: bytes) -> bytes:
    """Dynamic int8. A third of the size, and verified not to change behaviour."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "fp32.onnx"
        dst = Path(tmp) / "int8.onnx"
        src.write_bytes(fp32)
        quantize_dynamic(
            model_input=str(src),
            model_output=str(dst),
            weight_type=QuantType.QInt8,
        )
        return dst.read_bytes()


# ── the training run ─────────────────────────────────────────────────────

def train(active_rows, incumbent_auc: float | None = None,
          seed: int = 0) -> TrainResult:
    """One training run, all devices pooled into one model.

    A single model serves all three appliances; each window carries a device
    one-hot, so structure common to all of them -- an empty room means off, the
    daily rhythm, hysteresis -- is learned once rather than three times, while
    what differs per appliance still separates.
    """
    t0 = time.perf_counter()

    timelines: dict[str, list[Step]] = {}
    Xs, y_ons, y_levels, owners = [], [], [], []

    for device_id in devices.DEVICE_ORDER:
        timeline = synthesise(device_id, active_rows)
        timelines[device_id] = timeline
        X, y_on, y_level = sequence.build_windows(device_id, timeline)
        if len(X):
            Xs.append(X)
            y_ons.append(y_on)
            y_levels.append(y_level)
            owners.append(np.full(len(X), device_id, dtype=object))

    if not Xs:
        return TrainResult(ok=False, reason="no training windows")

    X = np.concatenate(Xs)
    y_on = np.concatenate(y_ons)
    y_level = np.concatenate(y_levels)
    owner = np.concatenate(owners)

    # Guardrail 1: enough data, and both classes present.
    if len(X) < MIN_WINDOWS:
        return TrainResult(ok=False, reason=f"only {len(X)} windows, need {MIN_WINDOWS}",
                           n_windows=len(X))
    if len(np.unique(y_on)) < 2:
        only = "on" if y_on[0] > 0.5 else "off"
        return TrainResult(ok=False, n_windows=len(X),
                           reason=f"every window is {only}; nothing to separate")

    # Guardrail 2: judged on cross-validated AUC, never training AUC -- an
    # overfit model wins on its own training data every time.
    cv_auc = _cross_val_auc(X, y_on, seed)
    if cv_auc is not None and cv_auc < MIN_CV_AUC:
        return TrainResult(ok=False, n_windows=len(X), cv_auc=cv_auc,
                           reason=f"cv auc {cv_auc:.3f} below {MIN_CV_AUC}")

    # Guardrail 3: a candidate must beat the incumbent.
    if incumbent_auc is not None and cv_auc is not None and cv_auc < incumbent_auc - 1e-9:
        return TrainResult(ok=False, n_windows=len(X), cv_auc=cv_auc,
                           reason=f"cv auc {cv_auc:.3f} does not beat incumbent "
                                  f"{incumbent_auc:.3f}")

    clf = _train_head(X, y_on, classifier=True, seed=seed)

    # The level head only learns from steps that are actually on. Training it on
    # off steps teaches it to predict the neutral placeholder.
    on_mask = y_on > 0.5
    reg = _train_head(X[on_mask], y_level[on_mask], classifier=False, seed=seed)

    level_mae = _level_mae_per_device(reg, X, y_level, owner, on_mask, seed)

    fp32 = _export_onnx(clf, reg)
    int8 = quantise_int8(fp32)

    warm_start = {
        device_id: _warm_day(timelines[device_id])
        for device_id in devices.DEVICE_ORDER
    }

    return TrainResult(
        ok=True,
        n_windows=len(X),
        params=count_params(),
        cv_auc=cv_auc,
        level_mae=level_mae,
        train_seconds=time.perf_counter() - t0,
        iterations=int(getattr(clf, "n_iter_", 0)),
        onnx_fp32=fp32,
        onnx_int8=int8,
        sha256=hashlib.sha256(int8).hexdigest(),
        warm_start=warm_start,
    )


def _warm_day(timeline: list[Step]) -> list:
    """The last trained day, indexed by hour of day.

    Indexed by hour rather than shipped as a flat 24-step window, because a flat
    window is only valid for ONE target hour. The first version shipped
    timeline[-24:], which ends at 23:00; the node then used it to predict 08:00,
    so the model saw a history whose last step was 23:00 while the context said
    08:00. Every prediction collapsed to off -- p_on 0.001 where the same model
    on a correctly aligned window gives 0.997.

    Indexed this way the node can rotate it to whatever hour it boots at, and
    the seeded window is both in-distribution and time-aligned.
    """
    by_hour: list = [None] * 24
    for step in timeline[-24:]:
        hour = time.localtime(step.ts).tm_hour
        by_hour[hour] = [bool(step.on), step.level, bool(step.occupied),
                         float(step.ambient_c)]
    return by_hour


def _cross_val_auc(X: np.ndarray, y: np.ndarray, seed: int) -> float | None:
    """Cross-validated AUC, used only as a gate.

    Three folds rather than five, and the fold models are capped at CV_MAX_ITER.
    The scored model is thrown away -- only the gate decision survives -- and a
    full-convergence fit per fold pushed a retrain past 25 seconds, which is
    unusable when someone is standing in front of the dashboard waiting for it.

    Deliberately n_jobs=1. Parallelising this made it SIX TIMES SLOWER on
    Windows (1.2 s -> 7.3 s): joblib spawns worker processes that each re-import
    scikit-learn, and that import dwarfs three fits of a 6,850-parameter model.

    Capping biases the score *down*, so the guardrail stays conservative: this
    can reject a model that would have passed, never admit one that should have
    failed. The shipped model is still trained to convergence.
    """
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.neural_network import MLPClassifier

    counts = np.bincount(y.astype(int))
    folds = int(min(CV_FOLDS, counts[counts > 0].min()))
    if folds < 2:
        return None

    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    estimator = MLPClassifier(
        hidden_layer_sizes=(HIDDEN,), activation="tanh", solver="adam",
        max_iter=CV_MAX_ITER, tol=1e-4, n_iter_no_change=10, random_state=seed,
    )
    scores = cross_val_score(estimator, X, y, cv=cv, scoring="roc_auc", n_jobs=1)
    return float(np.mean(scores))


def _level_mae_per_device(reg, X, y_level, owner, on_mask, seed) -> dict[str, float]:
    """MAE reported per device in its own unit.

    A single normalised number would be meaningless across mixed devices, where
    0.1 is a tenth of a degree for the AC and 200 kelvin for the light.

    The holdout is shuffled before splitting: the datasets are concatenated per
    device, so a tail split lands entirely inside the last device and reports
    nothing about the other two -- which is exactly what the first run did.
    """
    from sklearn.model_selection import train_test_split

    idx = np.arange(len(X))[on_mask]
    if len(idx) < 10:
        return {}

    train_idx, test_idx = train_test_split(idx, test_size=0.25, shuffle=True,
                                           random_state=seed)
    holdout = _train_head(X[train_idx], y_level[train_idx], classifier=False, seed=seed)
    predicted = holdout.predict(X[test_idx])

    out: dict[str, float] = {}
    for device_id in devices.DEVICE_ORDER:
        spec = devices.get(device_id)
        mask = owner[test_idx] == device_id
        if not mask.any():
            continue
        # Denormalise both sides before differencing, so the error is in the
        # device's own unit rather than in [-1, 1].
        got = np.array([spec.denormalise(float(v)) for v in predicted[mask]])
        want = np.array([spec.denormalise(float(v)) for v in y_level[test_idx][mask]])
        out[device_id] = float(np.mean(np.abs(got - want)))
    return out


# ── parity ───────────────────────────────────────────────────────────────

def parity(fp32: bytes, int8: bytes, samples: np.ndarray) -> dict:
    """int8 must behave like fp32, or it is not safe to ship."""
    import onnxruntime as ort

    def run(blob: bytes):
        session = ort.InferenceSession(blob, providers=["CPUExecutionProvider"])
        out = session.run(None, {"input": samples.astype(np.float32)})
        return out[0].ravel(), out[1].ravel()

    p_a, l_a = run(fp32)
    p_b, l_b = run(int8)

    decisions_match = int(np.sum((p_a >= 0.5) == (p_b >= 0.5)))
    return {
        "n": int(len(samples)),
        "max_p_on_delta": float(np.max(np.abs(p_a - p_b))),
        "mean_p_on_delta": float(np.mean(np.abs(p_a - p_b))),
        "max_level_delta": float(np.max(np.abs(l_a - l_b))),
        "decisions_identical": decisions_match == len(samples),
        "decisions_matched": decisions_match,
    }


# ── confidence gate ──────────────────────────────────────────────────────

def confidence(p_on: float, warm: bool, evidence: float = 1.0) -> float:
    """0.65 * decisiveness + 0.35 * evidence.

    A cold buffer never acts: until a real window exists the model is being
    asked about a day that never happened, and it can still look decisive, so
    confidence is capped below the act threshold. Acting on padding is how an
    automation does something inexplicable on its first morning.
    """
    decisiveness = abs(p_on - 0.5) * 2.0
    score = 0.65 * decisiveness + 0.35 * evidence
    return min(score, 0.74) if not warm else score


def gate(score: float) -> str:
    if score >= 0.75:
        return "act"
    if score >= 0.40:
        return "ask"
    return "abstain"
