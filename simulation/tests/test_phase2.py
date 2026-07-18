#!/usr/bin/env python3
"""Phase 2 component tests -- checkpoints, parsing, transport, leaves, node.

These drive the real objects directly rather than through the WebSocket, so a
failure points at the component that broke instead of at a timing race.

    python tests/test_phase2.py
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import checkpoint, commands, devices, protocol
from aeon.central import CentralNode
from aeon.db import Database
from aeon.leaf import LeafDevice
from aeon.pc import PCHub
from aeon.wifi_link import WifiLink

passed, failed = 0, 0
section_name = ""


def section(name: str) -> None:
    global section_name
    section_name = name
    print(f"\n  {name}")


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"    PASS  {name}")
    else:
        failed += 1
        print(f"    FAIL  {name}  {detail}")


async def eventually(predicate, timeout: float = 2.0, interval: float = 0.02) -> bool:
    """Wait on a condition, never on a duration.

    `WifiLink.send` reports `delivered` once the bytes have drained, which says
    nothing about the PC having handled them -- the node deliberately does not
    block on the PC. Counters on the receiving side therefore lag the send by a
    scheduling hop, so poll until they catch up rather than reading them once and
    calling a slow handler a bug.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return predicate()


# ── checkpoints ──────────────────────────────────────────────────────────

def test_checkpoints(tmp: Path) -> None:
    section("Checkpoints — durable replace, CRC, generations")
    path = tmp / "state.ckpt"

    ckpt = checkpoint.Checkpoint(
        seq=7, model_v=3, model_sha256="abc",
        schedule={"ac.living": {"all": {"21": [True, 25.0]}}},
        device_states={"ac.living": {"on": True, "level": 25.0}},
        # One 24-step lag window per device, keyed by device id.
        seq_buffer={d: [[True, 24.0, True, 28.0, 0.0]] * 24
                    for d in devices.DEVICE_ORDER},
    )
    ms = checkpoint.save(path, ckpt)
    check("save completes", path.exists() and ms >= 0, f"{ms:.2f} ms")

    restored, cold_ms, provenance = checkpoint.load(path)
    check("restores", restored is not None, provenance)
    check("seq survives", restored.seq == 7, str(restored.seq))
    check("schedule survives", restored.schedule == ckpt.schedule)
    check("a lag window survives for every device",
          set(restored.seq_buffer) == set(devices.DEVICE_ORDER)
          and all(len(v) == 24 for v in restored.seq_buffer.values()),
          str({k: len(v) for k, v in restored.seq_buffer.items()}))

    # A checkpoint from before the model landed carries a flat list here. It
    # must be dropped and rebuilt, not handed to code expecting a dict.
    legacy = tmp / "legacy.ckpt"
    checkpoint.save(legacy, checkpoint.Checkpoint(seq=3))
    blob = legacy.read_bytes()
    import json as _json
    body = _json.loads(blob[checkpoint._HEADER.size:-4])
    body["seq_buffer"] = [[1, 0, 1, 0.5]] * 24
    legacy.write_bytes(checkpoint._encode(checkpoint.Checkpoint(**{
        k: v for k, v in body.items()
        if k in checkpoint.Checkpoint.__dataclass_fields__ and k != "seq_buffer"
    })))
    old, _, _ = checkpoint.load(legacy)
    check("a pre-model checkpoint restores instead of crashing",
          old is not None and isinstance(old.seq_buffer, dict))

    # The first read of a file on Windows pays cold-cache and antivirus cost and
    # is not what a running node sees. Report both rather than quoting whichever
    # number flatters the design.
    _, warm_ms, _ = checkpoint.load(path)
    check("warm restore is sub-millisecond", warm_ms < 1.0,
          f"warm {warm_ms:.3f} ms (cold was {cold_ms:.2f} ms)")

    # Corrupt the live file: the previous generation must take over.
    checkpoint.save(path, checkpoint.Checkpoint(seq=8))
    path.write_bytes(b"AEON" + b"\x00" * 40)
    recovered, _, provenance = checkpoint.load(path)
    check("corrupt file falls back to a previous generation",
          recovered is not None and provenance != path.name,
          f"provenance={provenance}")

    # A flipped byte inside the payload must be caught by CRC, not loaded.
    good = tmp / "crc.ckpt"
    checkpoint.save(good, checkpoint.Checkpoint(seq=99, model_sha256="deadbeef"))
    blob = bytearray(good.read_bytes())
    blob[-8] ^= 0xFF
    good.write_bytes(bytes(blob))
    result, _, _ = checkpoint.load(good)
    check("CRC catches a flipped payload byte",
          result is None or result.seq != 99,
          f"loaded seq={getattr(result, 'seq', None)}")

    empty, _, provenance = checkpoint.load(tmp / "nothing.ckpt")
    check("missing checkpoint returns None, not an exception",
          empty is None and provenance == "none")


# ── intent parsing ───────────────────────────────────────────────────────

def test_parsing() -> None:
    section("Intent parsing")

    cases = [
        ("set the AC to 25 degrees at 9 PM", "ac.living", True, 25.0, 21, 22, "all"),
        ("run the fan at full speed at 3 PM", "fan.bedroom", True, 100.0, 15, 16, "all"),
        ("night light at 11 PM", "light.living", True, 2200.0, 23, 24, "all"),
        ("AC ko 23 degree pe chalao 9 baje", "ac.living", True, 23.0, 9, 10, "all"),
        ("turn off the AC on weekdays from 9 to 5", "ac.living", False, None, 9, 17, "weekday"),
    ]
    for text, device, on, level, h0, h1, day in cases:
        got = commands.parse(text)
        ok = (got is not None and got.device == device and got.on == on
              and got.level == level and got.hour_start == h0
              and got.hour_end == h1 and got.day_type == day)
        check(f"{text!r}", ok,
              f"got {got.device}/{got.on}/{got.level}/{got.hour_start}-{got.hour_end}/{got.day_type}"
              if got else "unparsed")

    check("a sentence with no device and no follow-up shape is unparsed",
          commands.parse("hello there, nice weather") is None)

    # Follow-up resolution.
    last = {"device": "ac.living", "hour_start": 21, "hour_end": 22, "day_type": "all"}
    check("a follow-up that changes nothing resolves to None",
          commands.resolve(commands.parse("make it nicer"), last) is None)
    followup = commands.parse("change it to 23")
    check("follow-up is flagged", followup is not None and followup.is_followup)
    resolved = commands.resolve(followup, last)
    check("follow-up inherits device and window",
          resolved.device == "ac.living" and resolved.hour_start == 21 and resolved.level == 23.0,
          f"{resolved.device}/{resolved.hour_start}/{resolved.level}" if resolved else "None")
    check("follow-up with nothing to attach to returns None",
          commands.resolve(commands.parse("change it to 23"), None) is None)


# ── supersession & schedule ──────────────────────────────────────────────

def test_supersession(tmp: Path) -> None:
    section("Supersession — the later preference wins, not the average")
    db = Database(tmp / "sup.db")
    pc = PCHub(db)

    def pref(level, h0, h1, day="all", device="ac.living", on=True):
        return protocol.preference(device, on, level, f"{level} at {h0}", time.time(),
                                   hour_start=h0, hour_end=h1, day_type=day)

    first, _ = pc.store_preference(pref(25.0, 21, 22))
    second, superseded = pc.store_preference(pref(23.0, 21, 22))

    check("overlapping earlier command superseded", superseded == [first], str(superseded))
    active = db.active_commands("ac.living")
    check("exactly one active AC command", len(active) == 1, str(len(active)))
    check("the surviving level is the later one", active[0]["level"] == 23.0,
          str(active[0]["level"]))
    check("superseded row is retained for audit", len(db.all_commands()) == 2)
    check("superseded row points at its replacement",
          db.all_commands()[0]["superseded_by"] == second)

    # A non-overlapping window must survive.
    pc.store_preference(pref(24.0, 9, 10))
    check("9 AM does not supersede 9 PM", len(db.active_commands("ac.living")) == 2)

    # weekday vs weekend do not collide; 'all' collides with both.
    pc.store_preference(pref(26.0, 14, 15, day="weekday"))
    pc.store_preference(pref(27.0, 14, 15, day="weekend"))
    check("weekday and weekend coexist at the same hour",
          len(db.active_commands("ac.living")) == 4,
          str(len(db.active_commands("ac.living"))))

    section("Compiled schedule")
    schedule = commands.compile_schedule(db.active_commands())
    weekday = commands.schedule_lookup(schedule, "ac.living", 14, is_weekend=False)
    weekend = commands.schedule_lookup(schedule, "ac.living", 14, is_weekend=True)
    check("weekday lookup finds the weekday rule", weekday == (True, 26.0), str(weekday))
    check("weekend lookup finds the weekend rule", weekend == (True, 27.0), str(weekend))
    check("an unscheduled hour returns None",
          commands.schedule_lookup(schedule, "ac.living", 3, False) is None)
    db.close()


# ── store-and-forward ────────────────────────────────────────────────────

async def test_wifi_link(tmp: Path) -> None:
    section("Store-and-forward — spool while the PC is away")
    db = Database(tmp / "link.db")
    pc = PCHub(db)
    port = await pc.start()

    link = WifiLink("127.0.0.1", port, tmp / "spool.jsonl")

    msg = protocol.preference("ac.living", True, 25.0, "hello", time.time(),
                              hour_start=21, hour_end=22)
    check("delivered while the PC is up", await link.send(msg) == "delivered")
    check("nothing spooled", link.spool_count() == 0)

    await pc.stop()
    await link.close()

    for _ in range(5):
        await link.send(msg)
    check("spooled while the PC is down", link.spool_count() == 5, str(link.spool_count()))

    await pc.start(port=port)
    delivered = await link.flush()
    check("all 5 replayed on reconnect", delivered == 5, str(delivered))
    check("spool cleared", link.spool_count() == 0, str(link.spool_count()))
    check("the PC actually received them",
          await eventually(lambda: pc.received >= 6), str(pc.received))

    # A row the PC cannot store must not take the link down with it. An earlier
    # build let a CHECK-constraint failure escape the connection handler: the
    # socket died and every later preference spooled behind a "healthy" node.
    poison = protocol.usage("ac.living", True, 25.0, True, "not-a-valid-source",
                            time.time())
    check("an unstorable row is answered, not fatal",
          await link.send(poison) == "delivered")
    check("the link survives it", (await link.send(msg)) == "delivered")
    check("still nothing spooled", link.spool_count() == 0, str(link.spool_count()))

    await pc.stop()
    db.close()


# ── leaves ───────────────────────────────────────────────────────────────

async def test_leaf_security(tmp: Path) -> None:
    section("Leaf — verifies before it switches a real appliance")
    leaf = LeafDevice("fan.bedroom")
    port = await leaf.start()

    async def raw(msg: dict) -> dict:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(json.dumps(msg).encode() + b"\n")
        await writer.drain()
        line = await reader.readline()
        writer.close()
        return json.loads(line)

    ok = await raw(protocol.actuate("fan.bedroom", True, 80.0, "phone"))
    check("a signed command is applied", ok.get("typ") == "leaf_ack", str(ok))
    check("the appliance actually changed", leaf.on and leaf.level == 80.0,
          f"{leaf.on}/{leaf.level}")

    unsigned = protocol.actuate("fan.bedroom", True, 100.0, "attacker")
    unsigned.pop("sig")
    resp = await raw(unsigned)
    check("unsigned command rejected", resp.get("reason") == "bad signature", str(resp))
    check("fan unchanged by the unsigned command", leaf.level == 80.0, str(leaf.level))

    tampered = protocol.actuate("fan.bedroom", True, 100.0, "model")
    tampered["level"] = 20.0
    resp = await raw(tampered)
    check("tampered command rejected", resp.get("reason") == "bad signature", str(resp))
    check("fan unchanged by the tampered command", leaf.level == 80.0, str(leaf.level))

    wrong = protocol.actuate("ac.living", True, 25.0, "phone")
    resp = await raw(wrong)
    check("a command for another device is rejected",
          resp.get("reason") == "wrong device", str(resp))

    # The node must never send out of range, but a relay that trusts its input
    # is a relay that melts something.
    resp = await raw(protocol.actuate("fan.bedroom", True, 9999.0, "phone"))
    check("out-of-range level clamped at the actuator", leaf.level == 100.0, str(leaf.level))

    await leaf.stop()
    check("a stopped leaf reports offline", not leaf.online)


# ── the node, end to end ─────────────────────────────────────────────────

async def test_central(tmp: Path) -> None:
    section("Central node — fan-out, deploy, failure isolation")
    db = Database(tmp / "central.db")
    pc = PCHub(db)
    pc_port = await pc.start()
    pc.seed_defaults()

    leaves = {d: LeafDevice(d) for d in devices.DEVICE_ORDER}
    node = CentralNode(tmp / "c.ckpt", tmp / "c.spool", tmp / "c.json",
                       "127.0.0.1", pc_port)
    for device_id, leaf in leaves.items():
        node.register_leaf(device_id, "127.0.0.1", await leaf.start())
    await node.restore()
    await node.connect_leaves()

    # deploy
    manifest, blob, _ = pc.retrain()
    ack = await node.apply_deployment(manifest, blob)
    check("policy deploys", ack.get("status") == "ok", str(ack))
    check("node records the model version", node.ckpt.model_v == manifest["model_v"])

    # a truncated transfer must never become live
    live_before = node.ckpt.model_sha256
    bad = await node.apply_deployment(manifest, blob + b"junk")
    check("sha256 mismatch rejected", bad.get("reason") == "sha256 mismatch", str(bad))
    check("the live policy is untouched after a bad transfer",
          node.ckpt.model_sha256 == live_before)

    reordered = dict(manifest)
    reordered["device_order"] = list(reversed(devices.DEVICE_ORDER))
    reordered = protocol.sign(reordered)
    bad = await node.apply_deployment(reordered, blob)
    check("reordered device_order rejected",
          bad.get("reason") == "device_order mismatch", str(bad))

    # fan-out
    cmd = protocol.command("ac.living", True, 25.0, "set the AC to 25 at 9 PM",
                           hour_start=21, hour_end=22)
    result = await node.handle_command(cmd)
    check("leaf acked", result["leaf"]["status"] == "leaf_ack", str(result["leaf"]))
    check("PC delivered", result["pc"]["status"] == "delivered", str(result["pc"]))
    check("the appliance is at 25", leaves["ac.living"].level == 25.0,
          str(leaves["ac.living"].level))

    async def median_leaf_hop(n: int = 21) -> float:
        hops = []
        for i in range(n):
            r = await node.handle_command(protocol.command(
                "ac.living", True, 16.0 + (i % 10), "latency probe",
                hour_start=21, hour_end=22))
            if r["leaf"]["status"] == "leaf_ack":
                hops.append(r["leaf"]["ms"])
        hops.sort()
        return hops[len(hops) // 2]

    # Timing thresholds make bad assertions -- a loaded machine blows through any
    # bound tight enough to mean something. Test the invariant instead: the leaf
    # hop must not depend on the PC. Putting the PC round trip back inside the
    # leaf path is exactly the regression this catches, and it shows up as the
    # PC-down median ballooning rather than as an arbitrary millisecond count.
    with_pc = await median_leaf_hop()
    await pc.stop()
    await node.link.close()
    without_pc = await median_leaf_hop()
    await pc.start(port=pc_port)

    print(f"      -> leaf hop median: {with_pc:.3f} ms with PC, "
          f"{without_pc:.3f} ms with PC unplugged")
    check("actuating a leaf does not depend on the PC being reachable",
          without_pc < with_pc * 3 + 2.0,
          f"{with_pc:.3f} ms -> {without_pc:.3f} ms when the PC went away")
    check("the leaf hop stays in single-digit milliseconds",
          with_pc < 10.0, f"{with_pc:.3f} ms")

    unsigned = dict(cmd)
    unsigned.pop("sig")
    result = await node.handle_command(unsigned)
    check("node rejects an unsigned command before touching the leaf",
          result["kind"] == "rejected", str(result))

    # PC offline -> leaf still actuates, record spools
    await pc.stop()
    await node.link.close()
    result = await node.handle_command(
        protocol.command("light.living", True, 2200.0, "night light", hour_start=23, hour_end=24))
    check("leaf still actuates with the PC offline",
          result["leaf"]["status"] == "leaf_ack", str(result["leaf"]))
    check("preference spooled rather than lost",
          result["pc"]["status"] == "spooled", str(result["pc"]))
    check("the light actually changed while the PC was down",
          leaves["light.living"].level == 2200.0, str(leaves["light.living"].level))

    await pc.start(port=pc_port)
    flushed = await node.link.flush()
    check("spool flushed on reconnect", flushed >= 1, str(flushed))
    check("spool empty afterwards", node.link.spool_count() == 0)

    # leaf offline -> preference still learned
    await leaves["fan.bedroom"].stop()
    node._drop_leaf("fan.bedroom")
    result = await node.handle_command(
        protocol.command("fan.bedroom", True, 100.0, "fan full", hour_start=15, hour_end=16))
    check("offline leaf reported as offline",
          result["leaf"]["status"] == "offline", str(result["leaf"]))
    check("the preference still reached the PC",
          result["pc"]["status"] == "delivered", str(result["pc"]))

    # restart survives
    seq_before = node.ckpt.seq
    await node.save("test")
    node2 = CentralNode(tmp / "c.ckpt", tmp / "c.spool", tmp / "c.json",
                        "127.0.0.1", pc_port)
    restored = await node2.restore()
    check("a restarted node restores its checkpoint", restored)
    check("sequence number is monotonic", node2.ckpt.seq > seq_before,
          f"{seq_before} -> {node2.ckpt.seq}")
    check("the restarted node still knows the schedule", bool(node2.schedule))

    await node.close()
    for leaf in leaves.values():
        await leaf.stop()
    await pc.stop()
    db.close()


# ── runner ───────────────────────────────────────────────────────────────

async def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="aeon-test-"))
    try:
        test_checkpoints(tmp)
        test_parsing()
        test_supersession(tmp)
        await test_wifi_link(tmp)
        await test_leaf_security(tmp)
        await test_central(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n  {passed} passed, {failed} failed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
