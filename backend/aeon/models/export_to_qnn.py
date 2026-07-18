"""
aeon/models/export_to_qnn.py — ONNX → QNN compilation pipeline.

Run this script once on the Snapdragon machine after training a new model
to produce the .bin files consumed by QNNRuntime.

Usage:
    python -m aeon.models.export_to_qnn --model presence_classifier
    python -m aeon.models.export_to_qnn --all

Requirements:
    - QNN SDK installed (qnn-net-run on PATH)
    - Input .onnx files in backend/models/src/
    - Output .bin files written to backend/models/bin/

QNN compilation targets HTP (Hexagon Tensor Processor) on Snapdragon X Elite.
"""

from __future__ import annotations

import argparse
import structlog
import shutil
import subprocess
from pathlib import Path

log = structlog.get_logger(__name__)

SRC_DIR = Path(__file__).parent / "src"
BIN_DIR = Path(__file__).parent / "bin"

MODELS = [
    "presence_classifier",
    "anomaly_detector",
    "occupancy_predictor",
]


def compile_model(name: str) -> bool:
    onnx_path = SRC_DIR / f"{name}.onnx"
    bin_path  = BIN_DIR / f"{name}.bin"

    if not onnx_path.exists():
        log.error("export.onnx_not_found", model=name, path=str(onnx_path))
        return False

    if not shutil.which("qnn-net-run"):
        log.error("export.qnn_sdk_not_on_path — install QNN SDK and add to PATH")
        return False

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    # qnn-onnx-converter: ONNX → QNN model library (.so + .bin)
    cmd = [
        "qnn-onnx-converter",
        "--input_network",      str(onnx_path),
        "--output_path",        str(BIN_DIR / name),
        "--backend",            "htp",
        "--quantization_overrides", str(SRC_DIR / f"{name}_quant.yaml"),
    ]

    log.info("export.compiling", model=name, cmd=" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("export.compile_failed", model=name, stderr=result.stderr)
        return False

    log.info("export.compile_ok", model=name, output=str(bin_path))
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s  %(message)s")
    parser = argparse.ArgumentParser(description="Export ONNX models to QNN .bin")
    parser.add_argument("--model", choices=MODELS,
                        help="Compile a specific model")
    parser.add_argument("--all", action="store_true",
                        help="Compile all models")
    args = parser.parse_args()

    targets = MODELS if args.all else ([args.model] if args.model else [])
    if not targets:
        parser.print_help()
        return

    ok = all(compile_model(m) for m in targets)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
