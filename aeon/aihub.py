"""Qualcomm AI Hub: compile, quantise and profile on real Snapdragon silicon.

What AI Hub is actually doing for us, stated plainly:

  * It compiles the exported ONNX for a chosen Snapdragon target and returns an
    optimised artefact (QNN / TFLite / ONNX depending on `target_runtime`).
  * It profiles that artefact on a real device in Qualcomm's device farm and
    returns measured inference latency and memory -- numbers taken from hardware
    rather than asserted in a slide.

What it is not doing, and should not be claimed:

  * The Arduino UNO Q's Dragonwing side is a QRB2210, a 4-series-class part with
    four Cortex-A53 cores. It does not carry the Hexagon NPU that a Snapdragon X
    Elite or an 8-series mobile part does, and AI Hub does not list it as a
    target. Inference on the UNO Q is CPU inference via ONNX Runtime -- entirely
    adequate for 6,850 parameters, but it is CPU.
  * So AI Hub profiling here answers "how does this artefact behave on
    Snapdragon hardware", which is a real and checkable claim, rather than
    "the Arduino runs it on an NPU", which would not be true.

Everything in this module is optional. Training, export, int8 quantisation and
deployment all work with AI Hub absent or unconfigured; `status()` says which.
"""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import sequence

# A Snapdragon X Elite target matches the AI PC in this project. Override per
# call; `list_devices()` prints what the account can actually reach.
DEFAULT_DEVICE = "Snapdragon X Elite CRD"


@dataclass
class HubStatus:
    installed: bool
    configured: bool
    version: str = ""
    detail: str = ""

    @property
    def usable(self) -> bool:
        return self.installed and self.configured


@dataclass
class OptimizeResult:
    ok: bool
    reason: str = ""
    device: str = ""
    target_runtime: str = ""
    compile_job: str = ""
    profile_job: str = ""
    artefact: bytes = b""
    artefact_name: str = ""
    inference_us: float | None = None
    peak_memory_mb: float | None = None
    compute_unit: str = ""
    elapsed_s: float = 0.0
    raw: dict = field(default_factory=dict)


def status() -> HubStatus:
    """Is AI Hub importable, and does it hold credentials?"""
    try:
        import qai_hub  # noqa: F401
    except ImportError:
        return HubStatus(False, False, detail="pip install qai-hub")

    import qai_hub

    # qai_hub exposes a packaging Version object here, not a string.
    version = str(getattr(qai_hub, "__version__", "?"))
    config = Path.home() / ".qai_hub" / "client.ini"
    if not config.exists():
        return HubStatus(
            True, False, version,
            detail="no API token: get one at https://aihub.qualcomm.com and run "
                   "`qai-hub configure --api_token <token>`",
        )
    return HubStatus(True, True, version, detail="ready")


def list_devices(limit: int = 40) -> list[str]:
    """Device names this account can target. Empty if unconfigured."""
    if not status().usable:
        return []
    import qai_hub
    try:
        return [d.name for d in qai_hub.get_devices()][:limit]
    except Exception:
        return []


def optimize(
    onnx_fp32: bytes,
    device_name: str = DEFAULT_DEVICE,
    target_runtime: str = "onnx",
    profile: bool = True,
    timeout_s: float = 900.0,
) -> OptimizeResult:
    """Compile (and optionally profile) the model on Snapdragon hardware.

    Returns ok=False with a reason rather than raising: a hackathon demo must
    not die because a cloud service was slow, and the locally quantised int8
    artefact is a perfectly good fallback.
    """
    state = status()
    if not state.usable:
        return OptimizeResult(ok=False, reason=state.detail, device=device_name)

    import qai_hub

    t0 = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "aeon_ts.onnx"
            src.write_bytes(onnx_fp32)

            device = qai_hub.Device(device_name)

            compile_job = qai_hub.submit_compile_job(
                model=str(src),
                device=device,
                # The node feeds one window at a time.
                input_specs={"input": (1, sequence.INPUT_DIM)},
                options=f"--target_runtime {target_runtime}",
            )
            compiled = compile_job.get_target_model()
            if compiled is None:
                return OptimizeResult(
                    ok=False, device=device_name, target_runtime=target_runtime,
                    compile_job=str(compile_job.job_id),
                    reason="compile job produced no model",
                    elapsed_s=time.perf_counter() - t0,
                )

            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            path = Path(compiled.download(str(out_dir)))
            artefact = path.read_bytes()

            result = OptimizeResult(
                ok=True,
                device=device_name,
                target_runtime=target_runtime,
                compile_job=str(compile_job.job_id),
                artefact=artefact,
                artefact_name=path.name,
                elapsed_s=time.perf_counter() - t0,
            )

            if profile:
                profile_job = qai_hub.submit_profile_job(model=compiled, device=device)
                summary = profile_job.download_profile()
                result.profile_job = str(profile_job.job_id)
                result.raw = _summarise(summary)
                result.inference_us = result.raw.get("inference_us")
                result.peak_memory_mb = result.raw.get("peak_memory_mb")
                result.compute_unit = result.raw.get("compute_unit", "")
                result.elapsed_s = time.perf_counter() - t0

            return result

    except Exception as exc:                        # noqa: BLE001 - never fatal
        return OptimizeResult(
            ok=False, device=device_name, target_runtime=target_runtime,
            reason=f"{type(exc).__name__}: {exc}",
            elapsed_s=time.perf_counter() - t0,
        )


def _summarise(summary) -> dict:
    """Pull the few numbers worth quoting out of AI Hub's profile blob.

    The schema has moved between client versions, so this reads defensively and
    returns what it finds rather than assuming a shape.
    """
    out: dict = {}
    if not isinstance(summary, dict):
        return out

    execution = summary.get("execution_summary") or {}
    for key in (
        "estimated_inference_time",
        "estimated_inference_time_microseconds",
        "inference_time",
    ):
        value = execution.get(key)
        if isinstance(value, (int, float)):
            out["inference_us"] = float(value)
            break

    for key in ("estimated_inference_peak_memory", "peak_memory_bytes"):
        value = execution.get(key)
        if isinstance(value, (int, float)):
            out["peak_memory_mb"] = float(value) / (1024 * 1024)
            break

    layers = summary.get("execution_detail") or []
    if isinstance(layers, list) and layers:
        units = {
            layer.get("compute_unit")
            for layer in layers
            if isinstance(layer, dict) and layer.get("compute_unit")
        }
        if units:
            out["compute_unit"] = ",".join(sorted(units))

    return out
