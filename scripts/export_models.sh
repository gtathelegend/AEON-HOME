#!/usr/bin/env bash
# scripts/export_models.sh — Compile ONNX models to QNN .bin for Hexagon NPU.
#
# Run this once on the Snapdragon X Elite machine after training.
# Requires the QNN SDK (qnn-onnx-converter) to be installed and on PATH.
#
# Usage: ./scripts/export_models.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/backend"
[ -d ".venv" ] && source .venv/bin/activate

echo "▶ Compiling all models to QNN .bin..."
python -m aeon.models.export_to_qnn --all
echo "✓ Models compiled to backend/models/bin/"
