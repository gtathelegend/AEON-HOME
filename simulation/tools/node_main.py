#!/usr/bin/env python3
"""Run the central node on the Arduino UNO Q.

This is the same CentralNode the demo runs in-process, started standalone on the
UNO Q's Dragonwing (Debian) side, talking to real leaves and a real PC over WiFi:

    python3 tools/node_main.py \
        --pc 192.168.1.42:9800 \
        --leaf ac.living=192.168.1.51:9001 \
        --leaf fan.bedroom=192.168.1.52:9001 \
        --leaf light.living=192.168.1.53:9001 \
        --data /var/lib/aeon

The node holds the model, runs every inference and routes every command. It does
not switch loads -- the leaves do that. It does not need the PC to run: the PC is
required to learn, never to run, so this keeps working with the laptop closed and
spools what it cannot deliver.

Sensors: --sensor simulated (default) generates the same daily curve the demo
uses. Wire a real DHT22 by replacing read_ambient().
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import devices, sim                     # noqa: E402
from aeon.central import CentralNode              # noqa: E402


def parse_leaf(spec: str) -> tuple[str, str, int]:
    """`device.id=host:port`"""
    device_id, _, address = spec.partition("=")
    host, _, port = address.partition(":")
    if device_id not in devices.REGISTRY:
        raise argparse.ArgumentTypeError(
            f"unknown device {device_id!r}; known: {devices.DEVICE_ORDER}")
    if not host or not port.isdigit():
        raise argparse.ArgumentTypeError(f"bad leaf address in {spec!r}")
    return device_id, host, int(port)


def read_ambient(now: float, simulated: bool) -> tuple[float, float, int]:
    """Temperature, humidity, motion for the whole zone.

    Replace this with a real sensor read on hardware. The node reads ambient for
    the zone; the leaves are dumb actuators and carry no sensors.
    """
    if simulated:
        lt = time.localtime(now)
        temp, rh = sim.ambient_at(lt.tm_hour + lt.tm_min / 60.0)
        return temp, rh, 1 if devices.default_occupancy(lt.tm_hour) else 0

    raise NotImplementedError(
        "wire a real sensor here, or run with --sensor simulated"
    )


async def run(args) -> int:
    data = Path(args.data)
    data.mkdir(parents=True, exist_ok=True)

    pc_host, _, pc_port = args.pc.partition(":")

    node = CentralNode(
        ckpt_path=data / "state.ckpt",
        spool_path=data / "spool.jsonl",
        model_path=data / "aeon_ts.onnx",
        pc_host=pc_host,
        pc_port=int(pc_port or 9800),
    )
    for device_id, host, port in args.leaf:
        node.register_leaf(device_id, host, port)

    restored = await node.restore()
    connected = await node.connect_leaves()

    print()
    print("  ÆON HOME · CENTRAL NODE")
    print("  " + "-" * 52)
    print(f"  data        {data}")
    print(f"  PC          {pc_host}:{pc_port}")
    print(f"  leaves      {connected}/{len(args.leaf)} connected")
    # Report restore and reconnect separately: eMMC restore is sub-millisecond,
    # WiFi association takes seconds. The node resumes CONTROLLING instantly and
    # resumes LEARNING when the network returns.
    if restored:
        print(f"  checkpoint  restored from {node.restore_from} in "
              f"{node.restore_ms:.2f} ms, seq {node.ckpt.seq}")
        print(f"  policy      v{node.ckpt.model_v} "
              f"{'ONNX loaded' if node.runner else 'schedule fallback'}")
        if node.runner:
            print(f"  provider    {node.runner.provider}")
    else:
        print("  checkpoint  none valid - safe defaults, everything off")
    print("  " + "-" * 52)
    print(f"  tick every {args.interval}s. Ctrl-C to stop.")
    print()

    stopping = asyncio.Event()

    def request_stop(*_):
        stopping.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, request_stop)
        except (ValueError, AttributeError):
            pass

    ticks = 0
    try:
        while not stopping.is_set():
            now = time.time()
            lt = time.localtime(now)
            temp, rh, motion = read_ambient(now, args.sensor == "simulated")
            occupied = bool(motion)

            changes = await node.tick(lt.tm_hour, lt.tm_wday >= 5, temp, occupied,
                                      ts=now)
            await node.send_telemetry(temp, rh, motion, now)
            ticks += 1

            for change in changes:
                spec = devices.get(change["device"])
                print(f"  {time.strftime('%H:%M:%S', lt)}  {spec.label:14} "
                      f"-> {spec.format_level(change['level']) if change['on'] else 'OFF'}")

            if args.verbose and ticks % 10 == 0:
                print(f"  [{time.strftime('%H:%M:%S', lt)}] {temp:.1f}°C "
                      f"occupied={occupied} spooled={node.link.spool_count()} "
                      f"inference={node.inference_us:.0f}us")

            try:
                await asyncio.wait_for(stopping.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
    finally:
        await node.save("shutdown")
        await node.close()
        print("\n  checkpoint saved, node stopped.\n")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AEON Home central node")
    ap.add_argument("--pc", default="127.0.0.1:9800", help="host:port of the AI PC")
    ap.add_argument("--leaf", action="append", type=parse_leaf, default=[],
                    metavar="device.id=host:port")
    ap.add_argument("--data", default="/var/lib/aeon")
    ap.add_argument("--interval", type=float, default=30.0,
                    help="control tick, seconds")
    ap.add_argument("--sensor", choices=("simulated", "real"), default="simulated")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not args.leaf:
        print("no leaves registered; pass --leaf device.id=host:port", file=sys.stderr)
        return 2

    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
