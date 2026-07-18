#!/usr/bin/env python3
"""Step the demo clock through 24 hours and print what the leaves actually do.

Values are read back from the leaf devices over the socket -- the number on the
appliance, not the number the model wished for.

    python run.py --reset       # terminal 1
    python tests/walk_day.py    # terminal 2
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

URL = "ws://127.0.0.1:8800/ws"


async def state(ws) -> dict:
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), 20))
        if msg.get("typ") == "state":
            return msg


async def main() -> int:
    async with websockets.connect(URL, max_size=8 * 1024 * 1024) as ws:
        snap = await state(ws)
        print(f"\n  policy v{snap['policy']['model_v']} "
              f"{snap['policy']['kind']} — pausing the clock\n")

        await ws.send(json.dumps({"typ": "pause"}))
        await state(ws)

        print("  hour  ambient   AC            FAN          LIGHT         source")
        print("  " + "-" * 68)

        on_counts = {d["id"]: 0 for d in snap["devices"]}

        for hour in range(24):
            await ws.send(json.dumps({"typ": "settime", "hour": hour}))
            snap = await state(ws)

            cells = []
            for device in snap["devices"]:
                cells.append(f"{device['level_text']:>11}")
                if device["on"]:
                    on_counts[device["id"]] += 1

            src = {d["source"] for d in snap["devices"]}
            occupied = "" if snap["ambient"]["occupied"] else "  (empty)"
            print(f"  {hour:02d}:00 {snap['ambient']['temp_c']:6.1f}°C "
                  + " ".join(cells)
                  + f"   {','.join(sorted(src))}{occupied}")

        print()
        for device_id, count in on_counts.items():
            verdict = "OK" if count else "NEVER ON"
            print(f"  {device_id:14} on for {count:2d}/24 hours   {verdict}")

        dead = [d for d, c in on_counts.items() if c == 0]
        await ws.send(json.dumps({"typ": "pause"}))
        print()
        if dead:
            print(f"  FAIL  these never switched on all day: {dead}")
            return 1
        print("  PASS  every device runs at some point in the day")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
