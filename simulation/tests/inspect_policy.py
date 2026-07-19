#!/usr/bin/env python3
"""Trigger a retrain on a running hub and print what actually got deployed.

    python run.py --reset          # terminal 1
    python tests/inspect_policy.py # terminal 2
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
INTERESTING = {"deploy", "train", "aihub", "rejected", "boot", "seed"}


async def main() -> int:
    async with websockets.connect(URL, max_size=8 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"typ": "retrain"}))

        seen: set[tuple[str, str]] = set()
        for _ in range(60):
            msg = json.loads(await asyncio.wait_for(ws.recv(), 30))
            if msg.get("typ") != "state":
                continue

            for event in reversed(msg["log"][:8]):
                if event["kind"] not in INTERESTING:
                    continue
                key = (event["kind"], event.get("text", "")[:70])
                if key in seen:
                    continue
                seen.add(key)
                print(f"  {event['kind']:9} {event.get('text', '')[:120]}")

            policy = msg["policy"]
            if policy["model_v"] > 0 and policy["cv_auc"] is not None:
                print()
                print(f"  POLICY   v{policy['model_v']}  {policy['kind']}  "
                      f"{policy['size_bytes']:,} B  cv_auc {policy['cv_auc']:.3f}  "
                      f"{policy['n_windows']:,} windows  {policy['params']:,} params  "
                      f"{policy['train_seconds']:.2f} s")
                print("  MAE     ", {k: v["text"] for k, v in policy["level_mae"].items()})
                print()
                print("  DEVICES  (read back from the leaves)")
                for d in msg["devices"]:
                    print(f"    {d['label']:14} {d['level_text']:>9}  "
                          f"src={d['source']:9} conf={d['confidence']:.2f} "
                          f"gate={d['gate']}")
                return 0

    print("  timed out waiting for a trained policy")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
