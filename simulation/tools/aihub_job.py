#!/usr/bin/env python3
"""One AI Hub compile + profile job, reported as JSON.

Runs INSIDE .venv-aihub -- the only environment where `qai_hub` is importable.
The hub invokes it as a subprocess (see aeon/aihub_runner.py) because qai-hub
pins protobuf back to 6.x and cannot share an environment with the runtime
stack. Writes its result to --out so the caller never has to parse the progress
bars the AI Hub client prints.

    .venv-aihub/Scripts/python tools/aihub_job.py \
        --model build/aeon_ts_fp32.onnx --device "Snapdragon X Elite CRD" \
        --out result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import aihub      # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="One AI Hub compile + profile job")
    ap.add_argument("--model", required=True, help="fp32 ONNX to compile")
    ap.add_argument("--device", default=aihub.DEFAULT_DEVICE)
    ap.add_argument("--out", required=True, help="where to write the JSON result")
    ap.add_argument("--no-profile", action="store_true")
    args = ap.parse_args()

    report = aihub.optimize(
        Path(args.model).read_bytes(),
        device_name=args.device,
        profile=not args.no_profile,
    )

    payload = {
        "ok": report.ok,
        "reason": report.reason,
        "device": report.device,
        "target_runtime": report.target_runtime,
        "compile_job": report.compile_job,
        "profile_job": report.profile_job,
        "artefact_bytes": len(report.artefact),
        "artefact_name": report.artefact_name,
        "inference_us": report.inference_us,
        "peak_memory_mb": report.peak_memory_mb,
        "compute_unit": report.compute_unit,
        "elapsed_s": report.elapsed_s,
    }
    Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
