#!/usr/bin/env python3
"""Phase 3: the sequence model, ONNX export, int8 quantisation, node inference.

    python tests/test_phase3.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import aihub, devices, sequence, tsmodel
from aeon.runner import NodeRunner
from aeon.sequence import SequenceBuffer, Step

passed, failed = 0, 0


def section(name: str) -> None:
    print(f"\n  {name}")


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"    PASS  {name}")
    else:
        failed += 1
        print(f"    FAIL  {name}  {detail}")


def local_midnight() -> float:
    """Midnight in LOCAL time.

    `time.time() - time.time() % 86400` is midnight UTC, which in IST is 05:30
    local. The context features read `time.localtime(ts).tm_hour`, so a UTC
    anchor shifts every predicted hour by the UTC offset and the model looks
    broken while being exactly right.
    """
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def preferences() -> list[dict]:
    """The demo's spoken preferences, in the shape the DB hands over."""
    now = time.time()
    return [
        {"device": "ac.living", "on_state": 1, "level": 25.0,
         "hour_start": 21, "hour_end": 23, "day_type": "all", "stated_at": now},
        {"device": "fan.bedroom", "on_state": 1, "level": 100.0,
         "hour_start": 13, "hour_end": 17, "day_type": "all", "stated_at": now},
        {"device": "light.living", "on_state": 1, "level": 6500.0,
         "hour_start": 8, "hour_end": 18, "day_type": "all", "stated_at": now},
        {"device": "light.living", "on_state": 1, "level": 2200.0,
         "hour_start": 23, "hour_end": 24, "day_type": "all", "stated_at": now},
        # Every device in DEVICE_ORDER needs at least one stated preference, or
        # it contributes no training windows and reports no MAE.
        {"device": "vacuum.home", "on_state": 1, "level": 70.0,
         "hour_start": 10, "hour_end": 12, "day_type": "all", "stated_at": now},
    ]


# ── shapes ───────────────────────────────────────────────────────────────

def test_shapes() -> None:
    section("Input layout")
    # Literals on purpose. These are canaries for silent layout drift, so they
    # are meant to fail the moment a device is added and force the change to be
    # deliberate -- deriving them from the same formula the source uses would
    # assert nothing at all.
    check("input dimension is 106",
          sequence.INPUT_DIM == 106, str(sequence.INPUT_DIM))
    check("96 window + 6 context + 4 device one-hot",
          sequence.WINDOW * sequence.CHANNELS == 96
          and sequence.CONTEXT == 6
          and len(devices.DEVICE_ORDER) == 4)
    check("parameter count is 6,914", tsmodel.count_params() == 6914,
          str(tsmodel.count_params()))

    buf = SequenceBuffer("ac.living")
    for hour in range(sequence.WINDOW):
        buf.push(Step(True, 24.0, True, 28.0, ts=hour * 3600.0))
    x = buf.model_input(time.time(), 29.0)
    check("model_input is [1, 106]", x.shape == (1, 106), str(x.shape))

    check("flat() alone is 96 values -- not a model input",
          len(buf.flat()) == 96, str(len(buf.flat())))

    # Off steps must not carry a level.
    off = SequenceBuffer("ac.living")
    off.push(Step(False, 25.0, True, 28.0, ts=0.0))
    check("an off step records no level", off.steps[-1].level is None,
          str(off.steps[-1].level))

    section("Alignment")
    aligned = SequenceBuffer("ac.living")
    base = time.time()
    for i in range(sequence.WINDOW):
        aligned.push(Step(True, 24.0, True, 28.0, ts=base + i * 3600))
    try:
        aligned.check_alignment(base + sequence.WINDOW * 3600)
        check("an aligned window passes", True)
    except sequence.AlignmentError as exc:
        check("an aligned window passes", False, str(exc))

    try:
        aligned.check_alignment(base + sequence.WINDOW * 3600 + 8 * 3600)
        check("a shifted window raises rather than warns", False, "no exception")
    except sequence.AlignmentError:
        check("a shifted window raises rather than warns", True)

    section("Lag window persists across a restart")
    state = buf.to_state()
    restored = SequenceBuffer.from_state("ac.living", state)
    a = buf.model_input(base, 29.0)
    b = restored.model_input(base, 29.0)
    check("predictions before and after a restart use identical input",
          np.array_equal(a, b))
    check("the window costs about a kilobyte",
          500 < len(str(state)) < 4000, f"{len(str(state))} chars")


# ── synthesis ────────────────────────────────────────────────────────────

def test_synthesis() -> None:
    section("Turning speech into training data")
    rows = preferences()
    timeline = tsmodel.synthesise("ac.living", rows, days=28)

    check("28 days x 24 hourly steps", len(timeline) == 28 * 24, str(len(timeline)))

    on_hours = {time.localtime(s.ts).tm_hour for s in timeline if s.on}
    check("the commanded hours are on", on_hours == {21, 22}, str(sorted(on_hours)))
    check("the AC runs at the stated 25 degrees",
          all(s.level == 25.0 for s in timeline if s.on))
    check("off steps carry no level",
          all(s.level is None for s in timeline if not s.on))

    # One row per timestep, never duplicated. Repeating a stated preference to
    # weight it fills the lag window with N copies of the same hour and the
    # model trains on histories that cannot physically occur.
    stamps = [s.ts for s in timeline]
    check("no duplicated timesteps", len(stamps) == len(set(stamps)))
    gaps = {round(b - a) for a, b in zip(stamps, stamps[1:])}
    check("steps are exactly one hour apart", gaps == {3600}, str(gaps))

    empty = [s for s in timeline if not devices.default_occupancy(time.localtime(s.ts).tm_hour)]
    check("nothing runs while the room is empty",
          all(not s.on for s in empty), f"{sum(s.on for s in empty)} on-steps")

    X, y_on, y_level = sequence.build_windows("ac.living", timeline)
    check("windows have 106 features", X.shape[1] == 106, str(X.shape))
    check("one window per predictable step",
          len(X) == len(timeline) - sequence.WINDOW, str(len(X)))
    check("both classes present", len(np.unique(y_on)) == 2)


# ── training ─────────────────────────────────────────────────────────────

def test_training() -> tsmodel.TrainResult:
    section("Training on the AI PC")
    result = tsmodel.train(preferences())

    check("training succeeded", result.ok, result.reason)
    if not result.ok:
        return result

    print(f"      -> {result.n_windows} windows, {result.params} params, "
          f"cv auc {result.cv_auc:.3f}, {result.train_seconds:.2f} s, "
          f"{result.iterations} iterations")

    check("pooled windows across all four devices", result.n_windows > 1500,
          str(result.n_windows))
    check("cross-validated AUC clears the guardrail",
          result.cv_auc is not None and result.cv_auc >= tsmodel.MIN_CV_AUC,
          str(result.cv_auc))
    check("trained to convergence, not to the iteration ceiling",
          0 < result.iterations < 3000, str(result.iterations))

    check("MAE reported per device in its own unit",
          set(result.level_mae) == set(devices.DEVICE_ORDER),
          str(list(result.level_mae)))
    for device_id, mae in result.level_mae.items():
        print(f"      -> {device_id:14} MAE {devices.get(device_id).format_error(mae)}")

    section("The deployment artefact")
    check("fp32 ONNX exported", len(result.onnx_fp32) > 0)
    check("int8 is materially smaller than fp32",
          len(result.onnx_int8) < len(result.onnx_fp32),
          f"{len(result.onnx_fp32)} -> {len(result.onnx_int8)}")
    print(f"      -> fp32 {len(result.onnx_fp32):,} B, int8 {len(result.onnx_int8):,} B")
    check("artefact fits in one WiFi message", len(result.onnx_int8) < 65536,
          f"{len(result.onnx_int8)} B")
    check("hashed for the node to verify", len(result.sha256) == 64)

    check("warm start covers every device",
          set(result.warm_start) == set(devices.DEVICE_ORDER))
    check("warm start is a full 24 steps each",
          all(len(v) == sequence.WINDOW for v in result.warm_start.values()),
          str({k: len(v) for k, v in result.warm_start.items()}))
    check("warm start is indexed by hour, not a flat window",
          all(row is not None and len(row) == 4
              for row in result.warm_start["light.living"]),
          str(result.warm_start["light.living"][:2]))
    return result


def test_warm_start_alignment(result: tsmodel.TrainResult) -> None:
    """The window must be time-aligned with the step being predicted.

    Shipping the last 24 training steps produced a window ending at 23:00, and
    the node then used it to predict 08:00. Every prediction collapsed to off --
    p_on 0.001 where the same model on an aligned window gives 0.997 -- and
    nothing in the outputs said why. This is that bug, pinned.
    """
    if not result.ok:
        return

    section("Warm start must be rotated to the target hour")
    runner = NodeRunner(result.onnx_int8)
    by_hour = result.warm_start["light.living"]
    spec = devices.get("light.living")
    base = local_midnight()

    def predict_at(hour: int, rotated: bool) -> tuple[float, float]:
        anchor = base + hour * 3600
        if rotated:
            steps = []
            for back in range(sequence.WINDOW, 0, -1):
                ts = anchor - back * 3600
                row = by_hour[time.localtime(ts).tm_hour]
                steps.append(Step(bool(row[0]), row[1], bool(row[2]),
                                  float(row[3]), ts))
        else:
            # The old, broken seeding: the trained day in fixed 00..23 order,
            # whatever hour we are actually predicting.
            steps = [Step(bool(r[0]), r[1], bool(r[2]), float(r[3]),
                          anchor - (24 - i) * 3600)
                     for i, r in enumerate(by_hour)]
        buf = SequenceBuffer("light.living", steps)
        p, lz = runner.run(buf.model_input(anchor, 26.0))
        return p, spec.denormalise(lz)

    p_day, level_day = predict_at(12, rotated=True)
    check("a rotated window predicts daylight at noon",
          p_day > 0.5 and level_day > 5500,
          f"p={p_day:.3f} level={level_day:.0f}K")

    p_night, level_night = predict_at(23, rotated=True)
    check("and the night light at 23:00",
          p_night > 0.5 and level_night < 2600,
          f"p={p_night:.3f} level={level_night:.0f}K")

    p_broken, _ = predict_at(12, rotated=False)
    check("an unrotated window is what collapsed the old build",
          p_broken < p_day,
          f"unrotated p={p_broken:.3f} vs rotated p={p_day:.3f}")

    section("Alignment is enforced, not assumed")
    anchor = base + 12 * 3600
    stale = SequenceBuffer("light.living", [
        Step(True, 6500.0, True, 26.0, anchor - (30 + i) * 3600)
        for i in range(sequence.WINDOW)
    ])
    try:
        stale.check_alignment(anchor)
        check("a stale window raises instead of predicting", False, "no exception")
    except sequence.AlignmentError:
        check("a stale window raises instead of predicting", True)


# ── guardrails ───────────────────────────────────────────────────────────

def test_guardrails(good: tsmodel.TrainResult) -> None:
    section("Guardrails -- a bad model must not reach the node")

    thin = tsmodel.train(preferences(), )
    # Too little data: synthesise only a couple of days.
    rows = preferences()
    tiny_timeline = tsmodel.synthesise("ac.living", rows, days=1)
    X, y, _ = sequence.build_windows("ac.living", tiny_timeline)
    check("one day yields too few windows to train on",
          len(X) < tsmodel.MIN_WINDOWS, str(len(X)))

    # Every window off: nothing to separate.
    silent = tsmodel.train([])
    check("a house with no preferences is rejected",
          not silent.ok, silent.reason)
    check("and says why", "window" in silent.reason or "separate" in silent.reason,
          silent.reason)

    # Candidate must beat the incumbent.
    if good.ok and good.cv_auc is not None:
        stale = tsmodel.train(preferences(), incumbent_auc=good.cv_auc + 0.05)
        check("a candidate that does not beat the incumbent is rejected",
              not stale.ok, stale.reason)
        check("the rejection names the incumbent",
              "incumbent" in stale.reason, stale.reason)

    section("Confidence gate")
    check("a decisive prediction on a warm buffer acts",
          tsmodel.gate(tsmodel.confidence(0.98, warm=True)) == "act")
    check("an uncertain prediction asks",
          tsmodel.gate(tsmodel.confidence(0.62, warm=True)) == "ask",
          str(tsmodel.confidence(0.62, warm=True)))
    # A cold buffer never acts: the model is being asked about a day that never
    # happened and can still look decisive.
    cold = tsmodel.confidence(0.999, warm=False)
    check("a cold buffer never reaches the act threshold",
          cold <= 0.74 and tsmodel.gate(cold) != "act", f"{cold:.3f}")


# ── parity and inference ─────────────────────────────────────────────────

def test_parity_and_inference(result: tsmodel.TrainResult) -> None:
    if not result.ok:
        return

    section("int8 vs fp32 parity")
    rows = preferences()
    timeline = tsmodel.synthesise("ac.living", rows)
    X, _, _ = sequence.build_windows("ac.living", timeline)
    samples = X[:300]

    report = tsmodel.parity(result.onnx_fp32, result.onnx_int8, samples)
    print(f"      -> over {report['n']} windows: max p_on delta "
          f"{report['max_p_on_delta']:.2e}, max level delta "
          f"{report['max_level_delta']:.2e}")
    check("on/off decisions identical between fp32 and int8",
          report["decisions_identical"],
          f"{report['decisions_matched']}/{report['n']}")
    check("p_on drift is negligible", report["mean_p_on_delta"] < 0.01,
          str(report["mean_p_on_delta"]))

    section("Running on the node")
    runner = NodeRunner(result.onnx_int8)
    p_on, level_z = runner.run(samples[:1])
    check("the node produces a probability", 0.0 <= p_on <= 1.0, str(p_on))
    check("and a level in normalised range", -1.5 <= level_z <= 1.5, str(level_z))

    bench = runner.benchmark(samples[:1], iterations=200)
    print(f"      -> {bench['provider']}: median {bench['median_us']:.1f} us, "
          f"p95 {bench['p95_us']:.1f} us")
    check("inference is well under a millisecond",
          bench["median_us"] < 1000, f"{bench['median_us']:.1f} us")

    section("The model drives the right behaviour")
    # Walk a day and read out what the model would do for the AC.
    decisions = {}
    for hour in range(24):
        idx = [i for i in range(len(timeline)) if time.localtime(timeline[i].ts).tm_hour == hour
               and i >= sequence.WINDOW]
        if not idx:
            continue
        i = idx[len(idx) // 2]
        buf = SequenceBuffer("ac.living", timeline[i - sequence.WINDOW:i])
        x = buf.model_input(timeline[i].ts, timeline[i].ambient_c)
        p, lz = runner.run(x)
        decisions[hour] = (p, devices.get("ac.living").denormalise(lz))

    on_hours = sorted(h for h, (p, _) in decisions.items() if p >= 0.5)
    check("the model learned the 9 PM AC preference", 21 in on_hours, str(on_hours))
    check("and does not run the AC at 3 AM", 3 not in on_hours, str(on_hours))
    if 21 in decisions:
        setpoint = decisions[21][1]
        check("at approximately the stated 25 degrees", abs(setpoint - 25.0) < 1.5,
              f"{setpoint:.2f} C")


# ── AI Hub ───────────────────────────────────────────────────────────────

def test_aihub() -> None:
    section("Qualcomm AI Hub")
    state = aihub.status()
    print(f"      -> installed={state.installed} configured={state.configured} "
          f"version={state.version}")
    print(f"      -> {state.detail}")

    check("the AI Hub client is importable", state.installed, state.detail)
    check("status() reports cleanly whether it is usable",
          isinstance(state.usable, bool))

    # Unconfigured must degrade, never raise: a demo cannot die because a cloud
    # service was unreachable.
    if not state.usable:
        result = aihub.optimize(b"not-a-real-model")
        check("optimize() degrades gracefully when unconfigured",
              not result.ok and bool(result.reason), result.reason)
        print("      -> skipping live compile/profile (no API token)")
    else:
        print(f"      -> devices: {aihub.list_devices(6)}")


async def test_node_drives_the_day(tmp: Path) -> None:
    """Deploy to a real node with real leaves, then walk a day.

    The end state that matters is not "the model scored well" but "every
    appliance actually switched". A model with CV AUC 1.0 that leaves every
    device off all day is the failure this catches.
    """
    section("Deployed model drives real leaves through a day")

    from aeon.central import CentralNode
    from aeon.db import Database
    from aeon.leaf import LeafDevice
    from aeon.pc import PCHub

    db = Database(tmp / "day.db")
    pc = PCHub(db)
    pc_port = await pc.start()
    pc.seed_defaults()

    leaves = {d: LeafDevice(d) for d in devices.DEVICE_ORDER}
    node = CentralNode(tmp / "day.ckpt", tmp / "day.spool", tmp / "day.onnx",
                       "127.0.0.1", pc_port)
    for device_id, leaf in leaves.items():
        node.register_leaf(device_id, "127.0.0.1", await leaf.start())
    await node.restore()
    await node.connect_leaves()

    manifest, blob, stats = pc.retrain()
    check("a model was produced", bool(manifest), stats.get("rejected", ""))
    if not manifest:
        await node.close()
        for leaf in leaves.values():
            await leaf.stop()
        await pc.stop()
        db.close()
        return

    ack = await node.apply_deployment(manifest, blob)
    check("the node accepted the model", ack.get("status") == "ok", str(ack))
    check("it is an int8 ONNX artefact, not a schedule",
          ack.get("kind") == "int8 ONNX", str(ack.get("kind")))
    check("and it was warm-started", ack.get("warm_started") is True)
    check("the node is running inference, not the fallback",
          node.runner is not None)

    midnight = local_midnight()
    on_hours = {d: [] for d in devices.DEVICE_ORDER}

    for hour in range(24):
        ts = midnight + hour * 3600
        occupied = devices.default_occupancy(hour)
        ambient = tsmodel.ambient_for_hour(hour)
        await node.tick(hour, False, ambient, occupied, ts=ts)
        for device_id, leaf in leaves.items():
            if leaf.on:
                on_hours[device_id].append(hour)

    for device_id, hours in on_hours.items():
        print(f"      -> {device_id:14} on at {hours}")

    check("the AC runs in the evening, as stated",
          any(h in (21, 22) for h in on_hours["ac.living"]),
          str(on_hours["ac.living"]))
    check("the fan runs in the afternoon",
          any(13 <= h < 17 for h in on_hours["fan.bedroom"]),
          str(on_hours["fan.bedroom"]))
    check("the light runs during the day",
          any(8 <= h < 18 for h in on_hours["light.living"]),
          str(on_hours["light.living"]))
    check("nothing runs while the room is empty",
          not any(h < 7 for hs in on_hours.values() for h in hs),
          str({d: [h for h in hs if h < 7] for d, hs in on_hours.items()}))

    # The self-fulfilling all-off spiral: a model that goes off and stays off.
    check("no device sits off for the entire day",
          all(hours for hours in on_hours.values()),
          str({d: len(h) for d, h in on_hours.items()}))

    check("the lag window persisted to the checkpoint",
          set(node.ckpt.seq_buffer) == set(devices.DEVICE_ORDER))

    await node.close()
    for leaf in leaves.values():
        await leaf.stop()
    await pc.stop()
    db.close()


async def main() -> int:
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="aeon-p3-"))
    try:
        test_shapes()
        test_synthesis()
        result = test_training()
        test_warm_start_alignment(result)
        test_guardrails(result)
        test_parity_and_inference(result)
        await test_node_drives_the_day(tmp)
        test_aihub()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n  {passed} passed, {failed} failed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
