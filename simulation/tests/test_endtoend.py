#!/usr/bin/env python3
"""End-to-end check: phone -> hub -> leaf + PC, over the real WebSocket.

Run the hub first:   python run.py --reset
Then:                python tests/test_endtoend.py

Works against either phase -- Phase 1's scripted house and Phase 2's real
sockets present the same state contract, which is the point of the seam.

Every assertion waits for a *condition* rather than for "the next snapshot".
The hub also broadcasts on a timer, so a snapshot can arrive that predates the
effect being tested; waiting on snapshot counts makes the suite flaky in a way
that looks like a product bug.
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
TIMEOUT = 12.0

passed, failed = 0, 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


async def next_state(ws, timeout: float = TIMEOUT) -> dict:
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout))
        if msg.get("typ") == "state":
            return msg


async def until(ws, predicate, timeout: float = TIMEOUT) -> tuple[dict, bool]:
    """Read snapshots until one satisfies `predicate`, or time out."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    state = await next_state(ws)
    while True:
        if predicate(state):
            return state, True
        if loop.time() >= deadline:
            return state, False
        try:
            state = await next_state(ws, timeout=max(0.1, deadline - loop.time()))
        except asyncio.TimeoutError:
            return state, False


def device(state: dict, device_id: str) -> dict:
    return next(d for d in state["devices"] if d["id"] == device_id)


def events(state: dict, kind: str) -> list[dict]:
    return [e for e in state["log"] if e["kind"] == kind]


def latest_fanout(state: dict, device_id: str) -> dict | None:
    for e in state["log"]:
        if e["kind"] == "fanout" and e.get("device") == device_id:
            return e
    return None


def ac_rows(state: dict) -> list[dict]:
    return [r for r in state["learned_week"] if r["device"] == "ac.living"]


async def main() -> int:
    async with websockets.connect(URL, max_size=4 * 1024 * 1024) as ws:
        state = await next_state(ws)
        check("hub sends a full snapshot on connect", state["typ"] == "state")
        check("all four devices present", len(state["devices"]) == 4)
        check("node is online", state["node"]["online"] is True)
        check("cloud bytes is zero", state["egress"]["cloud_bytes"] == 0)

        # --- a spoken preference fans out to two places -------------------
        await ws.send(json.dumps({"typ": "speak", "text": "set the AC to 25 degrees at 9 PM"}))
        state, ok = await until(ws, lambda s: (device(s, "ac.living")["on"]
                                               and device(s, "ac.living")["level"] == 25.0))
        check("AC actuated immediately", ok, str(device(state, "ac.living")))
        check("AC source is the phone", device(state, "ac.living")["source"] == "phone",
              device(state, "ac.living")["source"])

        fan = latest_fanout(state, "ac.living")
        check("fan-out event logged", fan is not None)
        if fan:
            check("leaf acked", fan["leaf"]["status"] == "leaf_ack", str(fan["leaf"]))
            check("PC received the preference", fan["pc"]["status"] == "delivered",
                  str(fan["pc"]))
            # A single sample over a real TCP socket on a loaded machine lands
            # around 1 ms and spikes past any tight bound. test_phase2.py tests
            # the property that actually matters -- that the leaf hop does not
            # depend on the PC -- over a median of many hops.
            print(f"        leaf hop {fan['leaf']['ms']:.3f} ms, "
                  f"pc hop {fan['pc']['ms']:.3f} ms")
            check("leaf hop is fast enough to feel immediate",
                  fan["leaf"]["ms"] < 25.0, f"{fan['leaf']['ms']} ms")

        state, ok = await until(ws, lambda s: any("21-22" in r["text"] for r in ac_rows(s)))
        check("preference learned at the STATED hour, not the clock hour", ok,
              str([r["text"] for r in ac_rows(state)]))

        # --- code-mixed Hindi/English -------------------------------------
        await ws.send(json.dumps({"typ": "speak", "text": "AC ko 23 degree pe chalao 9 baje"}))
        state, ok = await until(ws, lambda s: device(s, "ac.living")["level"] == 23.0)
        check("code-mixed sentence parsed", ok, str(device(state, "ac.living")["level"]))

        state, ok = await until(ws, lambda s: len(ac_rows(s)) == 2)
        check("9 baje (9 AM) does NOT supersede the 9 PM preference", ok,
              str([r["text"] for r in ac_rows(state)]))

        # --- supersession: the later preference wins, not the average ------
        await ws.send(json.dumps({"typ": "speak", "text": "set the AC to 23 degrees at 9 PM"}))
        state, ok = await until(ws, lambda s: sum(
            1 for r in ac_rows(s) if "21-22" in r["text"]) == 1 and any(
            "21-22" in r["text"] and "23.0" in r["text"] for r in ac_rows(s)))
        check("same-window preference superseded, not appended", ok,
              str([r["text"] for r in ac_rows(state)]))

        # --- PC offline: the leaf still actuates, the record spools --------
        await ws.send(json.dumps({"typ": "toggle_pc"}))
        state, ok = await until(ws, lambda s: not s["node"]["pc_reachable"])
        check("PC reported unreachable", ok)

        await ws.send(json.dumps({"typ": "speak", "text": "night light at 11 PM"}))
        state, ok = await until(ws, lambda s: (latest_fanout(s, "light.living") or {})
                                .get("pc", {}).get("status") == "spooled")
        check("record spooled instead of lost", ok,
              str(latest_fanout(state, "light.living")))

        fan = latest_fanout(state, "light.living")
        check("leaf still actuates with the PC offline",
              fan and fan["leaf"]["status"] == "leaf_ack", str(fan["leaf"] if fan else None))
        check("the light really changed while the PC was down",
              device(state, "light.living")["level"] == 2200.0,
              str(device(state, "light.living")["level"]))
        check("spool counter visible on the dashboard", state["egress"]["spooled"] >= 1,
              str(state["egress"]["spooled"]))

        # --- reconnect flushes the spool ----------------------------------
        await ws.send(json.dumps({"typ": "toggle_pc"}))
        state, ok = await until(ws, lambda s: (s["node"]["pc_reachable"]
                                               and s["egress"]["spooled"] == 0))
        check("spool flushed on reconnect", ok, str(state["egress"]["spooled"]))
        check("flush logged", bool(events(state, "flush")))

        # --- leaf offline: the preference is still learned -----------------
        await ws.send(json.dumps({"typ": "toggle_leaf", "device": "fan.bedroom"}))
        state, ok = await until(ws, lambda s: not device(s, "fan.bedroom")["online"])
        check("leaf reported offline", ok)

        await ws.send(json.dumps({"typ": "speak", "text": "run the fan at full speed at 3 PM"}))
        state, ok = await until(ws, lambda s: (latest_fanout(s, "fan.bedroom") or {})
                                .get("leaf", {}).get("status") == "offline")
        check("fan-out reports the leaf offline", ok,
              str(latest_fanout(state, "fan.bedroom")))
        fan = latest_fanout(state, "fan.bedroom")
        check("preference still reached the PC",
              fan and fan["pc"]["status"] == "delivered", str(fan["pc"] if fan else None))

        await ws.send(json.dumps({"typ": "toggle_leaf", "device": "fan.bedroom"}))
        state, ok = await until(ws, lambda s: device(s, "fan.bedroom")["online"])
        check("leaf back online", ok)

        # --- unsigned and tampered commands are rejected -------------------
        for mode in ("unsigned", "tampered"):
            before = len(events(state, "rejected"))
            await ws.send(json.dumps({"typ": "attack", "mode": mode}))
            state, ok = await until(ws, lambda s: len(events(s, "rejected")) > before)
            newest = events(state, "rejected")[0] if ok else {}
            check(f"{mode} command rejected",
                  ok and newest.get("reason") == "bad signature", str(newest))
            check(f"{mode} command left the device unchanged",
                  "BUT THE DEVICE CHANGED" not in str(newest.get("text", "")),
                  str(newest.get("text")))

        # --- the slow half of the two-speed loop ---------------------------
        # Speaking actuates the appliance now but deliberately does not redeploy
        # the versioned policy. So by this point there are undeployed changes,
        # and a retrain must pick them up. (Needs a hub started with --reset;
        # against a stale database the policy is already current and this fails
        # for a reason that has nothing to do with the code.)
        # Retrain and Redeploy are two buttons. Retrain trains and judges but
        # deploys nothing; the version must NOT move until Redeploy is pressed.
        before_v = state["policy"]["model_v"]
        await ws.send(json.dumps({"typ": "retrain"}))
        state, ok = await until(ws, lambda s: s["candidate"]["trained_at"] > 0,
                                timeout=90.0)
        check("retrain produces a candidate", ok,
              f"candidate={state['candidate']} (is the hub running with --reset?)")
        check("retrain alone deploys nothing",
              state["policy"]["model_v"] == before_v,
              f"{before_v} -> {state['policy']['model_v']}")
        check("the candidate is judged against the live model",
              state["candidate"]["better"] is not None
              and state["candidate"]["reason"] != "",
              str(state["candidate"]["reason"]))

        if state["candidate"]["better"]:
            await ws.send(json.dumps({"typ": "redeploy"}))
            state, ok = await until(ws, lambda s: s["policy"]["model_v"] > before_v,
                                    timeout=30.0)
            check("redeploy ships the candidate the preferences produced", ok,
                  f"{before_v} -> {state['policy']['model_v']}")
            check("deploy logged", bool(events(state, "deploy")))
            check("the candidate is cleared once deployed",
                  state["candidate"]["exists"] is False,
                  str(state["candidate"]["exists"]))
        else:
            check("redeploy ships the candidate the preferences produced", False,
                  f"candidate rejected: {state['candidate']['reason']}")
            check("deploy logged", False, "candidate was not deployable")
            check("the candidate is cleared once deployed", False, "never deployed")

        # An immediate second retrain must NOT offer a deployable candidate for
        # identical content, or the deployment log stops answering "when did
        # behaviour actually change?".
        settled_v = state["policy"]["model_v"]
        await ws.send(json.dumps({"typ": "retrain"}))
        state, ok = await until(
            ws, lambda s: s["candidate"]["trained_at"] > 0
            and not s["candidate"]["better"], timeout=90.0)
        check("retraining an unchanged policy offers nothing to deploy", ok,
              str(state["candidate"]["reason"]))
        check("and does not mint a new version",
              state["policy"]["model_v"] == settled_v,
              f"{settled_v} -> {state['policy']['model_v']}")

    print()
    print(f"  {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
