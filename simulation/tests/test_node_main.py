#!/usr/bin/env python3
"""The standalone node -- the thing that actually runs on the Arduino UNO Q.

    python tests/test_node_main.py

`tools/node_main.py` is the entry point for the UNO Q's Dragonwing side. It was
written and documented long before any board existed to run it on, which meant
the first time it executed would have been at a venue, on unfamiliar hardware,
against a physical appliance. This runs it here instead: a real subprocess, real
TCP leaves, a real PC, a real deployed int8 policy restored from a real
checkpoint.

What this does NOT prove: anything about the QRB2210, Debian, GPIO, WiFi
association or a physical relay. Those still need the board. What it does prove
is that the script starts, restores a policy, connects its leaves, drives them
from model inference, reaches the PC, and shuts down cleanly -- so that what is
left to discover on hardware is hardware, not a typo in the argument parser.

The flow mirrors a real deployment: the PC trains and pushes a policy to a node,
that node checkpoints it to eMMC, the node is then restarted (here: replaced by
the standalone process), and it must come back up controlling the house from
what it persisted.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import devices
from aeon.central import CentralNode
from aeon.db import Database
from aeon.leaf import LeafDevice
from aeon.pc import PCHub

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


async def eventually(predicate, timeout: float = 25.0, interval: float = 0.25) -> bool:
    """Wait on a condition, never on a duration -- a subprocess start is not
    a fixed cost, and a sleep long enough to be safe here is a sleep wasted on
    every run that was going to pass anyway."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return predicate()


async def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="aeon-node-"))
    node_data = tmp / "node"
    node_data.mkdir(parents=True, exist_ok=True)

    section("Staging a deployment, the way the PC would")
    db = Database(tmp / "pc.db")
    pc = PCHub(db)
    pc_port = await pc.start()
    seeded = pc.seed_defaults()
    check("the PC seeded preferences to train on", seeded > 0, str(seeded))

    leaves = {d: LeafDevice(d) for d in devices.DEVICE_ORDER}
    ports = {}
    for device_id, leaf in leaves.items():
        ports[device_id] = await leaf.start()
    check("every leaf is listening", len(ports) == len(devices.DEVICE_ORDER),
          str(len(ports)))

    manifest, blob, stats = pc.retrain()
    check("the PC produced a deployable policy", bool(manifest), stats.get("rejected", ""))
    if not manifest:
        return 1
    print(f"      -> {stats['kind']}, {len(blob):,} B, cv auc {stats['cv_auc']}")

    # Push it into the node's data directory, then drop that node. What remains
    # on disk is exactly what a UNO Q would hold after a deploy and a power cut.
    staging = CentralNode(
        ckpt_path=node_data / "state.ckpt",
        spool_path=node_data / "spool.jsonl",
        model_path=node_data / "aeon_ts.onnx",
        pc_host="127.0.0.1", pc_port=pc_port,
    )
    for device_id, port in ports.items():
        staging.register_leaf(device_id, "127.0.0.1", port)
    await staging.restore()
    ack = await staging.apply_deployment(manifest, blob)
    check("the node acked the deployment", ack.get("status") == "ok", str(ack))
    await staging.save("staged")
    await staging.close()

    check("a checkpoint is on disk for the standalone node to find",
          (node_data / "state.ckpt").exists())
    check("the int8 ONNX is on disk beside it",
          (node_data / "aeon_ts.onnx").exists())

    for leaf in leaves.values():
        leaf.on, leaf.level, leaf.applied_count = False, None, 0

    section("Running tools/node_main.py as a real process")
    argv = [
        sys.executable, "-u", str(ROOT / "tools" / "node_main.py"),
        "--pc", f"127.0.0.1:{pc_port}",
        "--data", str(node_data),
        "--sensor", "simulated",
        "--interval", "0.5",
        "--verbose",
    ]
    for device_id, port in ports.items():
        argv += ["--leaf", f"{device_id}=127.0.0.1:{port}"]

    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))

    banner_seen = await eventually(lambda: proc.poll() is not None or _has_output(proc))
    check("the process started without dying", proc.poll() is None,
          f"exit {proc.poll()}")
    if proc.poll() is not None:
        print(proc.stdout.read() if proc.stdout else "")
        return 1

    telemetry_before = db.telemetry_count()
    check("the standalone node reached the PC",
          await eventually(lambda: db.telemetry_count() > telemetry_before),
          f"telemetry {db.telemetry_count()}")

    check("it drove at least one leaf from its own inference",
          await eventually(lambda: any(l.applied_count for l in leaves.values())),
          str({d: l.applied_count for d, l in leaves.items()}))

    driven = {d: l.applied_count for d, l in leaves.items() if l.applied_count}
    print(f"      -> leaves actuated: {driven}")

    section("Shutting it down the way a power button would")
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)

    out = proc.stdout.read() if proc.stdout else ""
    check("it restored the staged policy rather than cold-starting",
          "checkpoint  restored" in out, out[:200])
    check("it loaded the ONNX rather than falling back to the schedule",
          "ONNX loaded" in out, out[:200])
    check("it reported which execution provider it got",
          "provider" in out, out[:200])

    for leaf in leaves.values():
        await leaf.stop()
    await pc.stop()
    db.close()

    print()
    print("  ---- node_main.py output ----")
    for line in out.splitlines()[:22]:
        print(f"  | {line}")

    return 0


def _has_output(proc) -> bool:
    return proc.stdout is not None


if __name__ == "__main__":
    code = asyncio.run(main())
    print(f"\n  {passed} passed, {failed} failed\n")
    sys.exit(1 if failed or code else 0)
