#!/usr/bin/env python3
"""Check a fresh machine can actually run ÆON Home. Run this FIRST.

    python tools/preflight.py

Written for the move to a Snapdragon X Elite (win-arm64) AI PC, where the usual
failure is a package with no ARM64 wheel: pip falls back to building from source
and either takes twenty minutes or fails outright. Better to know in thirty
seconds than at the demo.
"""

from __future__ import annotations

import importlib
import platform
import socket
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    ("fastapi", "hub HTTP + WebSocket"),
    ("uvicorn", "ASGI server"),
    ("websockets", "phone/dashboard socket"),
    ("numpy", "features and windows"),
    ("sklearn", "training (scikit-learn)"),
    ("onnx", "model export"),
    ("onnxruntime", "inference on the node"),
]
OPTIONAL = [
    ("qai_hub", "Qualcomm AI Hub compile/profile — optional"),
    ("requests", "used by dev scripts only"),
]

ok, warn, bad = [], [], []


def line(status: str, text: str) -> None:
    print(f"  {status:5} {text}")


def check_python() -> None:
    print("\n  PLATFORM")
    line("", f"{platform.system()} {platform.release()} / {platform.machine()}")
    line("", f"Python {sys.version.split()[0]} ({platform.architecture()[0]})")

    arm = platform.machine().lower() in ("arm64", "aarch64")
    if arm:
        line("OK", "ARM64 detected — this is the Snapdragon AI PC path")
    else:
        line("note", "not ARM64; fine for development, but re-measure on the X Elite")

    if sys.version_info < (3, 10):
        bad.append(f"Python {sys.version_info.major}.{sys.version_info.minor} is too old; need 3.10+")
        line("BAD", "Python 3.10+ required (the code uses `X | None` syntax)")
    else:
        ok.append("python")


def check_imports() -> None:
    print("\n  PACKAGES")
    for name, why in REQUIRED:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "?")
            line("OK", f"{name:14} {version:12} {why}")
            ok.append(name)
        except Exception as exc:
            line("BAD", f"{name:14} MISSING     {why}  ({type(exc).__name__})")
            bad.append(f"{name} missing — pip install -r requirements.txt")

    for name, why in OPTIONAL:
        try:
            module = importlib.import_module(name)
            line("OK", f"{name:14} {str(getattr(module, '__version__', '?')):12} {why}")
        except Exception:
            line("skip", f"{name:14} absent      {why}")
            warn.append(f"{name} not installed ({why})")


def check_onnx_runtime() -> None:
    print("\n  ONNX RUNTIME")
    try:
        import onnxruntime as ort
    except Exception:
        line("BAD", "onnxruntime not importable")
        return

    providers = ort.get_available_providers()
    line("", f"providers: {', '.join(providers)}")

    if "QNNExecutionProvider" in providers:
        line("OK", "QNN present — the Hexagon NPU is reachable on this machine")
        ok.append("qnn")
    else:
        line("note", "no QNN. Inference runs on CPU, which is fine at 6,914 params.")
        line("note", "For NPU on the X Elite: pip install onnxruntime-qnn")
        line("note", "(NodeRunner already prefers QNN when it is available.)")
        warn.append("QNNExecutionProvider absent — CPU inference")


def check_model_roundtrip() -> None:
    """The real test: can this machine train, export, quantise and infer?"""
    print("\n  MODEL PIPELINE")
    sys.path.insert(0, str(ROOT))
    try:
        import time

        import numpy as np

        from aeon import sequence, tsmodel
        from aeon.runner import NodeRunner

        rows = [
            {"device": "ac.living", "on_state": 1, "level": 25.0, "hour_start": 21,
             "hour_end": 23, "day_type": "all", "stated_at": time.time()},
            {"device": "light.living", "on_state": 1, "level": 6500.0, "hour_start": 7,
             "hour_end": 18, "day_type": "all", "stated_at": time.time()},
        ]

        t0 = time.perf_counter()
        tsmodel.warm_up()
        warm_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        result = tsmodel.train(rows)
        train_s = time.perf_counter() - t0

        if not result.ok:
            line("BAD", f"training rejected: {result.reason}")
            bad.append("model pipeline failed")
            return

        runner = NodeRunner(result.onnx_int8)
        bench = runner.benchmark(
            np.zeros((1, sequence.INPUT_DIM), dtype=np.float32), iterations=100)

        line("OK", f"trained {result.n_windows:,} windows, cv auc {result.cv_auc:.3f}")
        line("OK", f"int8 artefact {len(result.onnx_int8):,} B")
        line("OK", f"inference {bench['median_us']:.1f} us median on {bench['provider']}")
        line("", f"quantiser warm-up {warm_s:.1f} s, training {train_s:.1f} s")
        ok.append("pipeline")

        if train_s > 20:
            warn.append(f"training took {train_s:.0f}s — slow for a live demo")
    except Exception as exc:
        line("BAD", f"{type(exc).__name__}: {exc}")
        bad.append("model pipeline raised")


def check_network() -> None:
    print("\n  NETWORK")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()

    line("", f"LAN address {ip}")
    if ip.startswith("127."):
        line("note", "no LAN address — the phone will not reach the hub")
        warn.append("no LAN address detected")
    else:
        line("OK", f"phone URL will be http://{ip}:8800/phone")

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("0.0.0.0", 8800))
        line("OK", "port 8800 is free")
    except OSError:
        line("note", "port 8800 is in use — pass --port to run.py")
        warn.append("port 8800 busy")
    finally:
        probe.close()

    line("note", "Windows Firewall will prompt on first run. ALLOW on private")
    line("note", "networks, or the phone cannot reach the dashboard.")


def check_android() -> None:
    print("\n  ANDROID APP (optional)")
    app = ROOT / "AEON app"
    if not app.exists():
        line("skip", "no AEON app/ directory")
        return

    key = app / "local.properties"
    if key.exists() and "sarvam.key" in key.read_text(encoding="utf-8", errors="ignore"):
        line("OK", "local.properties has a sarvam.key")
    else:
        line("note", "no sarvam.key in AEON app/local.properties — voice will be off")
        warn.append("Sarvam key not present on this machine (copy it out of band)")

    try:
        out = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=20)
        version = (out.stderr or out.stdout).splitlines()[0] if (out.stderr or out.stdout) else "?"
        line("OK", f"java present: {version.strip()}")
    except Exception:
        line("note", "no java on PATH — Android Studio ships its own JDK")


def main() -> int:
    print("\n  ÆON HOME — PREFLIGHT")
    print("  " + "=" * 56)
    check_python()
    check_imports()
    check_onnx_runtime()
    check_network()
    check_model_roundtrip()
    check_android()

    print("\n  " + "=" * 56)
    if bad:
        print(f"  {len(bad)} BLOCKER(S):")
        for item in bad:
            print(f"    - {item}")
    if warn:
        print(f"  {len(warn)} note(s):")
        for item in warn:
            print(f"    - {item}")
    if not bad:
        print("\n  READY. Next: python run.py --reset")
    print()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
