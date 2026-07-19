"""Run a Qualcomm AI Hub job from the hub, without importing qai_hub.

`qai-hub` pins protobuf back to 6.x while the runtime stack here is on 7.x, and
`onnx` sits on protobuf's C extension -- so installing it beside the hub would
downgrade protobuf underneath the ONNX export path the whole system depends on.
It lives in a separate virtualenv instead (`.venv-aihub`, see docs/AIHUB.md).

That leaves the hub unable to `import qai_hub` at all, which is fine: an AI Hub
job is a slow, optional, offline step, so it runs as a SUBPROCESS in that other
venv and reports back as JSON. The isolation is the point, not a workaround.

A profile job took 365 s against a 2 s training run. Nothing here may ever be
awaited inside a button press.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def interpreter() -> Path | None:
    """The isolated venv's python, or None if it was never built.

    Searched under `simulation/` and under the repo root above it, because the
    venv is a local artefact that may sit either side of that boundary and is
    gitignored, so it does not move when the source does.
    """
    for base in (ROOT, ROOT.parent):
        for rel in (Path(".venv-aihub") / "Scripts" / "python.exe",
                    Path(".venv-aihub") / "bin" / "python"):
            candidate = base / rel
            if candidate.exists():
                return candidate
    return None


def available() -> tuple[bool, str]:
    exe = interpreter()
    if exe is None:
        return False, ("no .venv-aihub -- python -m venv .venv-aihub && "
                       ".venv-aihub/Scripts/pip install -r requirements.txt qai-hub")
    if not (Path.home() / ".qai_hub" / "client.ini").exists():
        return False, ("no API token -- get one at https://aihub.qualcomm.com then "
                       ".venv-aihub/Scripts/qai-hub configure --api_token <token>")
    return True, "ready"


async def optimize(onnx_fp32: bytes, device_name: str,
                   timeout_s: float = 1200.0) -> dict:
    """Compile + profile on Snapdragon silicon. Never raises.

    Returns a dict with ok/reason and, when it worked, the measured numbers.
    """
    ok, reason = available()
    if not ok:
        return {"ok": False, "reason": reason, "device": device_name}

    exe = interpreter()
    with tempfile.TemporaryDirectory() as tmp:
        model_path = Path(tmp) / "candidate_fp32.onnx"
        out_path = Path(tmp) / "result.json"
        model_path.write_bytes(onnx_fp32)

        proc = await asyncio.create_subprocess_exec(
            str(exe), str(ROOT / "tools" / "aihub_job.py"),
            "--model", str(model_path),
            "--device", device_name,
            "--out", str(out_path),
            cwd=str(ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "reason": f"timed out after {timeout_s:.0f}s",
                    "device": device_name}

        if out_path.exists():
            try:
                return json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        tail = (stdout or b"").decode("utf-8", "replace").strip().splitlines()
        return {"ok": False, "device": device_name,
                "reason": tail[-1] if tail else f"exit {proc.returncode}"}
