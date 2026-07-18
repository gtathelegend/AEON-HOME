"""Phase 2 source: the real system.

Wires the AI PC (SQLite + TCP server), the central node (checkpoints, routing,
store-and-forward) and three leaf devices (real TCP servers that verify HMAC
before switching), then adapts all of it to the same HubState the dashboard
already renders.

Everything crosses a socket. On the bench the leaves are loopback ports; on the
table they are ESP32s on the WiFi speaking exactly this protocol. What is still
simulated: the ambient sensor feed, and the policy, which is a compiled schedule
until Phase 3 replaces it with a trained model.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from . import commands, devices, protocol, sequence, sim, tsmodel
from .central import CentralNode
from .db import Database
from .hubstate import HubState
from .leaf import LeafDevice
from .pc import PCHub


class LiveHouse:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

        self.state = HubState()
        self.db = Database(self.dir / "aeon.db")
        self.pc = PCHub(self.db)
        self.leaves: dict[str, LeafDevice] = {
            d: LeafDevice(d) for d in devices.DEVICE_ORDER
        }
        self.central = CentralNode(
            ckpt_path=self.dir / "state.ckpt",
            spool_path=self.dir / "spool.jsonl",
            model_path=self.dir / "policy.json",
        )

        self.demo_hour = 8.0
        self.paused = False
        self.started = False

    # -- bring the house up ------------------------------------------------

    async def start(self) -> None:
        s = self.state

        # Pay the quantiser's ~8 s import cost now, not when someone presses
        # Retrain in front of judges.
        warm = tsmodel.warm_up()

        pc_port = await self.pc.start()
        self.central.set_pc("127.0.0.1", pc_port)
        seeded = self.pc.seed_defaults()
        if warm > 1.0:
            s.event("boot", text=f"ONNX quantiser warmed in {warm:.1f} s")

        for device_id, leaf in self.leaves.items():
            port = await leaf.start()
            self.central.register_leaf(device_id, "127.0.0.1", port)

        restored = await self.central.restore()
        await self.central.connect_leaves()
        s.node_online = True
        s.restore_ms = self.central.restore_ms

        if restored:
            s.event("boot", text=(
                f"checkpoint restored from {self.central.restore_from} in "
                f"{self.central.restore_ms:.2f} ms, seq {self.central.ckpt.seq}, "
                f"policy v{self.central.ckpt.model_v}"
            ))
        else:
            s.event("boot", text="no valid checkpoint - safe defaults, everything off")

        if seeded:
            s.event("seed", text=f"{seeded} default preferences seeded into SQLite")

        # A node with no policy cannot run a house. Compile and deploy one.
        if not self.central.schedule:
            await self.deploy()

        s.ckpt_seq = self.central.ckpt.seq
        self.started = True

    # -- deploy ------------------------------------------------------------

    async def deploy(self, force: bool = False, use_aihub: bool = False) -> dict:
        s = self.state

        manifest, blob, stats = self.pc.retrain(use_aihub=use_aihub)

        if not manifest:
            # A rejected candidate never leaves the PC; the deployed model
            # stays live.
            s.event("rejected", reason=stats.get("rejected", "training failed"),
                    text=f"model not deployed; v{s.policy.model_v} stays live")
            return {"status": "rejected", "reason": stats.get("rejected")}

        if not force and manifest["sha256"] == self.central.ckpt.model_sha256:
            s.event("train", text="policy unchanged - nothing to deploy")
            return {"status": "unchanged"}

        deployment_id = self.db.record_deployment(
            manifest["model_v"], manifest["sha256"], manifest["size_bytes"])

        ack = await self.central.apply_deployment(manifest, blob)

        if ack.get("status") == "ok":
            self.db.ack_deployment(deployment_id)
            s.policy.model_v = ack["model_v"]
            s.policy.size_bytes = ack["bytes"]
            s.policy.kind = manifest.get("kind", "schedule")
            s.policy.sha256 = manifest["sha256"]
            s.policy.n_windows = stats["n_windows"]
            s.policy.params = stats["params"]
            s.policy.cv_auc = stats["cv_auc"]
            s.policy.train_seconds = stats["train_secs"]
            s.policy.level_mae = stats.get("level_mae") or {}
            s.policy.trained_at = time.time()
            s.event("deploy", text=(
                f"{ack['bytes']:,} B {stats.get('kind', '')} -> sha256 verified -> "
                f"ack v{ack['model_v']}, warm-start {sequence.WINDOW} steps x "
                f"{len(ack['devices'])} devices; leaves received nothing"
            ))

            report = stats.get("aihub")
            if report and report.get("ok"):
                s.event("aihub", text=(
                    f"AI Hub {report['device']}: {report['inference_us']:.0f} us "
                    f"on {report['compute_unit'] or 'device'} "
                    f"(compile {report['compile_job']})"
                ))
            elif report:
                s.event("aihub", text=f"AI Hub skipped - {report['reason']}")
        else:
            s.event("rejected", reason=ack.get("reason", "deploy failed"),
                    text=f"policy v{manifest['model_v']} not loaded; previous policy stays live")
        return ack

    # -- control loop ------------------------------------------------------

    async def tick(self) -> None:
        s = self.state
        hour = int(self.demo_hour) % 24
        temp, rh = sim.ambient_at(self.demo_hour)
        lt = time.localtime()
        is_weekend = lt.tm_wday >= 5

        s.clock_ts = time.mktime(lt[:3] + (hour, int((self.demo_hour % 1) * 60), 0, 0, 0, -1))
        s.temp_c, s.rh_pct = temp, rh
        s.occupied = devices.default_occupancy(hour)
        s.motion = 1 if s.occupied else 0

        await self.central.tick(hour, is_weekend, temp, s.occupied, ts=s.clock_ts)
        await self.central.send_telemetry(temp, rh, s.motion, time.time())

    # -- state adaptation --------------------------------------------------

    def sync(self) -> None:
        """Copy the real system's state into what the screens render.

        Device on/level are read back from the LEAF -- the number on the
        appliance, not the number the policy wished for.
        """
        s = self.state

        for device_id, leaf in self.leaves.items():
            decided = self.central.device_states[device_id]
            ds = s.devices[device_id]
            ds.on = leaf.on
            ds.level = leaf.level
            ds.online = leaf.online
            ds.source = decided.get("src", "idle")
            ds.confidence = decided.get("confidence", 0.0)
            ds.gate = "act" if ds.confidence >= 0.75 else (
                "ask" if ds.confidence >= 0.40 else "abstain")

        s.node_online = True
        s.ckpt_seq = self.central.ckpt.seq
        s.restore_ms = self.central.restore_ms
        s.pc_reachable = self.pc.reachable
        s.link = "connected" if self.central.link.connected else "down"

        s.spooled = self.central.link.spool_count()
        s.local_packets = self.central.local_packets
        s.cloud_bytes = 0

        self._refresh_policy_display()
        s.learned_week = self.pc.learned_rows()

    def _refresh_policy_display(self) -> None:
        """Rebuild the policy panel from what actually persisted.

        Without this a restarted node showed a live model version next to a
        blank hash and no artefact size: those fields were only ever written by
        deploy(), which correctly does not run when the restored policy is
        already current.
        """
        s = self.state
        model_v = self.central.ckpt.model_v
        if s.policy.model_v == model_v and s.policy.sha256:
            return

        s.policy.model_v = model_v
        s.policy.sha256 = self.central.ckpt.model_sha256

        deployment = self.db.deployment_for(model_v)
        if deployment is not None:
            s.policy.size_bytes = deployment["size_bytes"]

        model = self.db.model_for(model_v)
        if model is not None:
            s.policy.n_windows = model["n_windows"] or 0
            s.policy.params = model["params"] or 0
            s.policy.cv_auc = model["cv_auc"]
            s.policy.train_seconds = model["train_secs"] or 0.0
            s.policy.trained_at = model["trained_at"] or 0.0

    # -- source contract ---------------------------------------------------

    async def run(self, bcast) -> None:
        if not self.started:
            await self.start()
            self.sync()
            await bcast.send(self.state.snapshot())

        while True:
            if not self.paused:
                self.demo_hour = (self.demo_hour + 1.0) % 24
                await self.tick()
            self.sync()
            await bcast.send(self.state.snapshot())
            await asyncio.sleep(sim.SECONDS_PER_HOUR)

    async def on_message(self, msg: dict, bcast) -> None:
        typ = msg.get("typ")
        s = self.state

        if typ == "speak":
            await self._speak(msg.get("text", ""))

        elif typ == "command":
            # A tile or slider on the phone: an instruction for right now.
            hour = int(self.demo_hour) % 24
            await self._dispatch(
                device_id=msg["device"], on=bool(msg.get("on")), level=msg.get("level"),
                spoken=msg.get("spoken", "manual control"),
                hour_start=hour, hour_end=hour + 1, day_type=commands.DAY_ALL,
            )

        elif typ == "retrain":
            s.event("train", text="compiling active preferences into a policy")
            self.sync()
            await bcast.send(s.snapshot())
            await self.deploy()

        elif typ == "toggle_pc":
            await self._toggle_pc()

        elif typ == "toggle_leaf":
            await self._toggle_leaf(msg["device"])

        elif typ == "attack":
            await self._attack(msg.get("mode", "unsigned"))

        elif typ == "pause":
            self.paused = not self.paused
            s.event("clock", text=f"demo clock {'paused' if self.paused else 'running'}")

        elif typ == "settime":
            self.demo_hour = float(msg.get("hour", 9)) % 24
            await self.tick()

        self.sync()
        await bcast.send(s.snapshot())

    # -- handlers ----------------------------------------------------------

    async def _speak(self, text: str) -> None:
        s = self.state
        intent = commands.parse(text)
        if intent is None:
            s.event("unparsed", text=f"could not identify a device in: {text!r}")
            return

        last = self.db.last_active_command()
        resolved = commands.resolve(intent, dict(last) if last else None)
        if resolved is None or resolved.device is None:
            s.event("unparsed", text=f"nothing to attach the follow-up to: {text!r}")
            return

        await self._dispatch(
            device_id=resolved.device, on=resolved.on, level=resolved.level,
            spoken=resolved.spoken, hour_start=resolved.hour_start,
            hour_end=resolved.hour_end, day_type=resolved.day_type,
        )

    async def _dispatch(self, device_id: str, on: bool, level: float | None,
                        spoken: str, hour_start: int, hour_end: int,
                        day_type: str) -> None:
        s = self.state
        msg = protocol.command(device_id, on, level, spoken,
                               hour_start=hour_start, hour_end=hour_end,
                               day_type=day_type)
        result = await self.central.handle_command(msg)

        if result["kind"] == "rejected":
            s.event("rejected", device=result.get("device"),
                    reason=result["reason"], text="command not applied")
            return

        s.event("fanout", device=device_id, label=devices.get(device_id).label,
                spoken=spoken, leaf=result["leaf"], pc=result["pc"])

        # Deliberately no redeploy here. The loop has two speeds: the appliance
        # responds NOW (the leaf hop above), and the versioned policy changes on
        # retrain. Collapsing them means one correction rewrites a weekly rhythm,
        # and it also makes "Retrain" a no-op by the time anyone presses it.

    async def _toggle_pc(self) -> None:
        s = self.state
        if self.pc.reachable:
            await self.pc.stop()
            await self.central.link.close()
            s.event("link", text="PC unreachable - preferences will spool to eMMC")
        else:
            await self.pc.start(port=self.pc.port)
            flushed = await self.central.link.flush()
            if flushed:
                s.event("flush", text=(
                    f"reconnected, flushed {flushed} spooled record(s) - "
                    f"the PC has learned them; retrain to deploy"))
            else:
                s.event("link", text="PC reachable again")

    async def _toggle_leaf(self, device_id: str) -> None:
        s = self.state
        leaf = self.leaves[device_id]
        label = devices.get(device_id).label
        if leaf.online:
            await leaf.stop()
            self.central._drop_leaf(device_id)
            s.event("leaf_link", device=device_id, text=f"{label} unplugged")
        else:
            await leaf.start()
            s.event("leaf_link", device=device_id, text=f"{label} back online")

    async def _attack(self, mode: str) -> None:
        """Send a hostile command to a leaf over a real socket.

        Not a simulated check: this opens a TCP connection from outside the
        node, exactly as a laptop on the same WiFi would, and the leaf's own
        verification is what rejects it.
        """
        s = self.state
        target = "fan.bedroom"
        leaf = self.leaves[target]

        if not leaf.online:
            s.event("rejected", reason="target offline",
                    text="plug the fan leaf back in to run this demo")
            return

        forged = protocol.actuate(target, True, 100.0, src="attacker")
        if mode == "tampered":
            forged["level"] = 100.0
            forged["on"] = True
            forged["device"] = target
            forged["src"] = "model"        # signed, then modified after signing
        else:
            forged.pop("sig", None)        # never signed at all

        before = (leaf.on, leaf.level)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", leaf.port), timeout=2.0)
            writer.write(json.dumps(forged).encode() + b"\n")
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), timeout=2.0)
            writer.close()
            response = json.loads(line) if line else {}
        except (OSError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
            s.event("rejected", reason="no response", text=str(exc))
            return

        after = (leaf.on, leaf.level)
        if response.get("status") == "rejected":
            s.event("rejected", device=target, reason=response.get("reason", "rejected"),
                    text=f"{mode} command from the same WiFi"
                         + ("" if before == after else " BUT THE DEVICE CHANGED"))
        else:
            s.event("accepted", device=target, reason="verified",
                    text=f"{mode} command was ACCEPTED - this is a bug")

    # -- shutdown ----------------------------------------------------------

    async def close(self) -> None:
        await self.central.close()
        for leaf in self.leaves.values():
            await leaf.stop()
        await self.pc.stop()
        self.db.close()
