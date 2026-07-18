#!/usr/bin/env python3
"""Does the house remember? Kill the hub, restart it, check nothing was lost.

Run against a hub started WITHOUT --reset, after test_endtoend.py has driven it:

    python run.py --reset          # terminal 1
    python tests/test_endtoend.py  # terminal 2
    # ...restart terminal 1 without --reset...
    python tests/test_restart.py

Or let this script do the whole thing:

    python tests/test_restart.py --managed
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

URL = "ws://127.0.0.1:8800/ws"
passed, failed = 0, 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


async def snapshot(timeout: float = 90.0, ready: bool = True) -> dict:
    """Wait for a snapshot from a hub that has finished booting.

    A screen that connects mid-startup gets an honest but empty state: the node
    is not online yet. Taking that first frame as "what survived the restart"
    reports total data loss for a hub that is merely still warming up -- and
    Phase 3's boot got a lot slower (quantiser warm-up, first training run), so
    what used to be a rare race became every run.
    """
    deadline = time.monotonic() + timeout
    last: dict | None = None
    while time.monotonic() < deadline:
        try:
            async with websockets.connect(URL, max_size=8 * 1024 * 1024) as ws:
                while time.monotonic() < deadline:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), 15.0))
                    if msg.get("typ") != "state":
                        continue
                    last = msg
                    if not ready or msg["node"]["online"]:
                        return msg
        except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException):
            await asyncio.sleep(0.5)
    if last is not None:
        return last
    raise RuntimeError("hub never came up")


def spawn(reset: bool) -> subprocess.Popen:
    args = [sys.executable, "run.py", "--port", "8800"]
    if reset:
        args.append("--reset")
    return subprocess.Popen(args, cwd=str(ROOT),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def drive(ws_sentences: list[str]) -> None:
    async with websockets.connect(URL, max_size=4 * 1024 * 1024) as ws:
        for text in ws_sentences:
            await ws.send(json.dumps({"typ": "speak", "text": text}))
            await asyncio.sleep(0.6)
        await ws.send(json.dumps({"typ": "retrain"}))
        # Training is a real run now, not a schedule compile.
        await asyncio.sleep(12.0)


async def main() -> int:
    managed = "--managed" in sys.argv
    proc = None

    if managed:
        print("\n  starting a fresh hub...")
        proc = spawn(reset=True)
        await snapshot()
        print("  speaking three preferences and deploying...")
        await drive([
            "set the AC to 25 degrees at 9 PM",
            "run the fan at full speed at 3 PM",
            "night light at 11 PM",
        ])

    before = await snapshot()
    print()

    ac_before = [r["text"] for r in before["learned_week"] if r["device"] == "ac.living"]
    check("there is something to lose", bool(ac_before) and before["policy"]["model_v"] > 0,
          f"model_v={before['policy']['model_v']} ac={ac_before}")

    model_v = before["policy"]["model_v"]
    sha = before["policy"]["sha256"]
    learned = sorted(r["text"] + r["device"] for r in before["learned_week"])
    ckpt_seq = before["node"]["ckpt_seq"]

    if managed:
        print("  killing the hub (no clean shutdown)...")
        proc.kill()
        proc.wait(timeout=10)
        await asyncio.sleep(1.0)
        print("  restarting WITHOUT --reset...\n")
        proc = spawn(reset=False)
    else:
        print("  >> restart the hub now WITHOUT --reset, then press Enter")
        input()

    after = await snapshot()

    check("the node restored a checkpoint rather than cold-starting",
          after["node"]["ckpt_seq"] >= ckpt_seq,
          f"seq {ckpt_seq} -> {after['node']['ckpt_seq']}")
    check("the deployed policy version survived",
          after["policy"]["model_v"] == model_v,
          f"v{model_v} -> v{after['policy']['model_v']}")
    check("the policy is byte-identical, not recompiled differently",
          after["policy"]["sha256"] == sha,
          f"{sha} -> {after['policy']['sha256']}")
    check("every learned preference survived",
          sorted(r["text"] + r["device"] for r in after["learned_week"]) == learned,
          f"{len(learned)} -> {len(after['learned_week'])}")
    # The design doc quotes 0.1-0.4 ms, measured on the UNO Q's Linux eMMC and
    # warm. This is the first read of the file in a brand-new process on Windows,
    # which is tens of milliseconds. Still instant to a person, but not the same
    # number, and worth reporting as what it is.
    print(f"      -> cold restore {after['node']['restore_ms']:.1f} ms")
    check("restore is fast enough to be invisible",
          after["node"]["restore_ms"] < 250.0, f"{after['node']['restore_ms']} ms")
    check("the node is running the house again", after["node"]["online"])

    if managed and proc is not None:
        proc.kill()
        proc.wait(timeout=10)

    print()
    print(f"  {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
