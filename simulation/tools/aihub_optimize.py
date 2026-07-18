#!/usr/bin/env python3
"""Compile and profile the ÆON model on Qualcomm AI Hub.

    python tools/aihub_optimize.py --devices          # what can this account target?
    python tools/aihub_optimize.py                    # train, compile, profile
    python tools/aihub_optimize.py --device "Snapdragon X Elite CRD"
    python tools/aihub_optimize.py --runtime tflite --out build/

First:

    pip install qai-hub
    qai-hub configure --api_token <token>     # from https://aihub.qualcomm.com

What this gets you that local export does not: the artefact is compiled for a
specific Snapdragon target and profiled on that silicon in Qualcomm's device
farm, so the latency and memory numbers are measured on hardware rather than
asserted.

What it does not get you: the Arduino UNO Q's Dragonwing side is a QRB2210 with
four Cortex-A53 cores and no Hexagon NPU of the kind an X Elite or an 8-series
part carries, and AI Hub does not list it as a target. Inference on the UNO Q is
CPU inference through ONNX Runtime -- fine for 6,914 parameters, but CPU. Profile
here to characterise the model on Snapdragon; deploy the int8 ONNX to the node.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import aihub, devices, sequence, tsmodel      # noqa: E402
from aeon.db import Database                  # noqa: E402
from aeon.runner import NodeRunner            # noqa: E402


def load_preferences(db_path: Path):
    """Train on what the house has actually been told, if there is a database."""
    if db_path.exists():
        db = Database(db_path)
        rows = [dict(r) for r in db.active_commands()]
        db.close()
        if rows:
            return rows, f"{len(rows)} active preferences from {db_path}"

    now = time.time()
    rows = [
        {"device": "ac.living", "on_state": 1, "level": 25.0, "hour_start": 21,
         "hour_end": 23, "day_type": "all", "stated_at": now},
        {"device": "fan.bedroom", "on_state": 1, "level": 70.0, "hour_start": 13,
         "hour_end": 17, "day_type": "all", "stated_at": now},
        {"device": "light.living", "on_state": 1, "level": 6500.0, "hour_start": 7,
         "hour_end": 18, "day_type": "all", "stated_at": now},
        {"device": "light.living", "on_state": 1, "level": 2200.0, "hour_start": 23,
         "hour_end": 24, "day_type": "all", "stated_at": now},
    ]
    return rows, "built-in demo preferences (no database found)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile/profile on Qualcomm AI Hub")
    ap.add_argument("--device", default=aihub.DEFAULT_DEVICE)
    ap.add_argument("--runtime", default="onnx",
                    choices=("onnx", "tflite", "qnn_lib_aarch64_android", "qnn_context_binary"))
    ap.add_argument("--devices", action="store_true", help="list targets and exit")
    ap.add_argument("--data", default="data/aeon.db")
    ap.add_argument("--out", default="build")
    ap.add_argument("--no-profile", action="store_true")
    args = ap.parse_args()

    state = aihub.status()
    print()
    print(f"  AI Hub client : {'installed v' + state.version if state.installed else 'MISSING'}")
    print(f"  credentials   : {'configured' if state.configured else 'NOT configured'}")
    if not state.configured:
        print(f"  -> {state.detail}")

    if args.devices:
        names = aihub.list_devices(60)
        if not names:
            print("\n  no devices (client unconfigured)\n")
            return 1
        print(f"\n  {len(names)} targets:")
        for name in names:
            print(f"    {name}")
        print()
        return 0

    rows, provenance = load_preferences(ROOT / args.data)
    print(f"  training on   : {provenance}")

    tsmodel.warm_up()
    result = tsmodel.train(rows)
    if not result.ok:
        print(f"\n  training rejected: {result.reason}\n")
        return 1

    print(f"  model         : {result.n_windows:,} windows, {result.params:,} params, "
          f"cv auc {result.cv_auc:.3f}, {result.train_seconds:.2f} s")
    print(f"  artefact      : fp32 {len(result.onnx_fp32):,} B -> "
          f"int8 {len(result.onnx_int8):,} B")
    for device_id, mae in result.level_mae.items():
        print(f"                  {device_id:14} MAE "
              f"{devices.get(device_id).format_error(mae)}")

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "aeon_ts_fp32.onnx").write_bytes(result.onnx_fp32)
    (out / "aeon_ts_int8.onnx").write_bytes(result.onnx_int8)
    (out / "warm_start.json").write_text(json.dumps(result.warm_start), encoding="utf-8")
    print(f"  written       : {out}/aeon_ts_int8.onnx (sha256 {result.sha256[:16]})")

    # Local baseline, so the AI Hub number has something to be compared against.
    runner = NodeRunner(result.onnx_int8)
    import numpy as np
    sample = np.zeros((1, sequence.INPUT_DIM), dtype=np.float32)
    bench = runner.benchmark(sample, iterations=200)
    print(f"  local ({bench['provider'].replace('ExecutionProvider', '')}): "
          f"median {bench['median_us']:.1f} us, p95 {bench['p95_us']:.1f} us")

    if not state.usable:
        print("\n  Skipping AI Hub: no credentials. The int8 ONNX above is a complete,")
        print("  deployable artefact -- AI Hub adds measured on-device numbers, not")
        print("  a dependency.\n")
        return 0

    print(f"\n  submitting to AI Hub: {args.device} / {args.runtime} ...")
    report = aihub.optimize(
        result.onnx_fp32,
        device_name=args.device,
        target_runtime=args.runtime,
        profile=not args.no_profile,
    )

    if not report.ok:
        print(f"  FAILED: {report.reason}\n")
        return 1

    print(f"  compile job   : {report.compile_job}")
    if report.profile_job:
        print(f"  profile job   : {report.profile_job}")
    print(f"  artefact      : {report.artefact_name} ({len(report.artefact):,} B)")
    if report.inference_us is not None:
        print(f"  ON DEVICE     : {report.inference_us:.0f} us median"
              f"{' on ' + report.compute_unit if report.compute_unit else ''}")
    if report.peak_memory_mb is not None:
        print(f"  peak memory   : {report.peak_memory_mb:.2f} MB")
    print(f"  elapsed       : {report.elapsed_s:.0f} s")

    if report.artefact:
        target = out / report.artefact_name
        target.write_bytes(report.artefact)
        print(f"  written       : {target}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
