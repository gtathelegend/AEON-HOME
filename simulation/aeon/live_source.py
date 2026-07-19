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

from . import aihub, aihub_runner, commands, devices, protocol, sequence, sim, tsmodel
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
        self.demo_day = 0        # simulated days elapsed; the clock must not loop
        self._midnight: float | None = None
        # A trained-but-undeployed (manifest, blob, stats), held between the
        # Retrain and Redeploy buttons.
        self._held: tuple[dict, bytes, dict] | None = None
        self._aihub_task: asyncio.Task | None = None
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

    async def retrain_candidate(self, bcast=None) -> dict:
        """Train and judge. Deploy nothing.

        The two-button split: this produces a candidate and a verdict, Redeploy
        acts on the verdict. Keeping them apart is what lets the screen say
        "better than what is running" BEFORE anything reaches the node, and what
        lets Redeploy stay disabled when it is not.
        """
        s = self.state
        c = s.candidate

        # Hand the deployed model over so it can be re-scored on the same data
        # the candidate is judged on, rather than compared against the figure it
        # earned on an easier dataset. See tsmodel.score_deployed().
        live_onnx = None
        try:
            if self.central.model_path.exists():
                live_onnx = self.central.model_path.read_bytes()
        except OSError:
            pass

        manifest, blob, stats = self.pc.retrain(incumbent_onnx=live_onnx)

        # Record the comparison whether or not it is deployable -- "not better"
        # is a result worth showing, not an error to hide.
        c.trained_at = time.time()
        # Prefer the incumbent re-scored on this dataset; fall back to its stored
        # figure only when it could not be scored.
        c.incumbent_auc = (stats.get("incumbent_auc_measured")
                           if stats.get("incumbent_auc_measured") is not None
                           else s.policy.cv_auc)
        c.incumbent_mae = dict(s.policy.level_mae or {})
        c.cv_auc = stats.get("cv_auc")
        c.level_mae = stats.get("level_mae") or {}
        c.n_windows = stats.get("n_windows", 0)
        c.stated_windows = stats.get("stated_windows", 0)
        c.observed_windows = stats.get("observed_windows", 0)
        c.observed_hours = sum((stats.get("observed_hours") or {}).values())
        c.train_seconds = stats.get("train_secs", 0.0)
        c.size_bytes = manifest.get("size_bytes", 0) if manifest else 0

        if not manifest:
            self._held = None
            c.exists = c.better = False
            c.reason = stats.get("rejected", "training failed")
            s.event("rejected", reason=c.reason,
                    text=f"candidate not deployable; v{s.policy.model_v} stays live")
            return {"status": "rejected", "reason": c.reason}

        if manifest["sha256"] == self.central.ckpt.model_sha256:
            self._held = None
            c.exists = c.better = False
            c.reason = "identical to the deployed policy - nothing new to learn"
            s.event("train", text=c.reason)
            return {"status": "unchanged"}

        self._held = (manifest, blob, stats)
        c.exists = c.better = True
        c.reason = "passed every guardrail and beats the incumbent"

        s.event("train", text=(
            f"candidate trained: {c.n_windows:,} windows "
            f"({c.stated_windows:,} stated + {c.observed_windows:,} observed"
            f"{f', {c.observed_hours:,} h recorded' if c.observed_hours else ''}), "
            f"cv auc {c.cv_auc:.3f} vs "
            f"{'none' if c.incumbent_auc is None else f'{c.incumbent_auc:.3f}'} live, "
            f"{c.size_bytes:,} B int8 - ready to deploy"
        ))

        # AI Hub runs in the background. A profile job took 365 s; awaiting it
        # here would freeze the button for six minutes mid-demo.
        self._start_aihub(bcast)
        return {"status": "candidate", "cv_auc": c.cv_auc}

    async def deploy_candidate(self) -> dict:
        """Push the held candidate to the node. Only reachable when it is better."""
        if not self._held:
            self.state.event("rejected", reason="no candidate",
                             text="train a model before deploying one")
            return {"status": "no-candidate"}

        manifest, blob, stats = self._held
        ack = await self._apply(manifest, blob, stats)
        if ack.get("status") == "ok":
            self._held = None
            self.state.candidate.exists = False
            self.state.candidate.better = False
            self.state.candidate.reason = "deployed"
        return ack

    def _start_aihub(self, bcast=None) -> None:
        """Fire a compile + profile job for the candidate, in the background.

        Never awaited by a caller. AI Hub measured 365 s for one job against a
        2 s training run: inside the button press that is six minutes of frozen
        screen in a five-minute demo. The dashboard shows `running` and fills in
        when it lands, or reports why it could not.
        """
        result = getattr(self.pc, "last_result", None)
        if result is None or not result.onnx_fp32:
            return

        if self._aihub_task and not self._aihub_task.done():
            return                      # one job at a time

        s = self.state
        ok, reason = aihub_runner.available()
        if not ok:
            s.aihub.state = "unavailable"
            s.aihub.reason = reason
            s.event("aihub", text=f"AI Hub unavailable - {reason}")
            return

        s.aihub.state = "running"
        s.aihub.reason = ""
        s.aihub.device = aihub.DEFAULT_DEVICE
        s.aihub.local_us = None
        s.event("aihub", text=(
            f"submitting compile + profile to AI Hub ({aihub.DEFAULT_DEVICE}) - "
            f"runs in the background, typically several minutes"
        ))

        async def run(fp32: bytes) -> None:
            report = await aihub_runner.optimize(fp32, aihub.DEFAULT_DEVICE)
            a = s.aihub
            a.elapsed_s = report.get("elapsed_s") or 0.0
            if report.get("ok"):
                a.state = "done"
                a.inference_us = report.get("inference_us")
                a.peak_memory_mb = report.get("peak_memory_mb")
                a.compute_unit = report.get("compute_unit") or ""
                a.compile_job = report.get("compile_job") or ""
                a.profile_job = report.get("profile_job") or ""
                a.artefact_bytes = report.get("artefact_bytes") or 0
                s.event("aihub", text=(
                    f"AI Hub {a.device}: {a.inference_us:.0f} us on "
                    f"{a.compute_unit or 'device'}, peak {a.peak_memory_mb:.1f} MB "
                    f"(compile {a.compile_job}, profile {a.profile_job}, "
                    f"{a.elapsed_s:.0f} s)"
                ))
            else:
                a.state = "failed"
                a.reason = report.get("reason", "unknown")
                s.event("aihub", text=f"AI Hub job failed - {a.reason}")

            self.sync()
            if bcast is not None:
                await bcast.send(s.snapshot())

        self._aihub_task = asyncio.create_task(run(result.onnx_fp32))

    async def deploy(self, force: bool = False, use_aihub: bool = False) -> dict:
        """Train and deploy in one step. Used to bootstrap a node with no policy."""
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

        return await self._apply(manifest, blob, stats)

    async def _apply(self, manifest: dict, blob: bytes, stats: dict) -> dict:
        s = self.state
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

            # Say where the training set came from. "2,592 windows" alone does
            # not distinguish a model that only ever re-learned the rules it was
            # given from one that has started learning the house.
            observed = stats.get("observed_windows") or 0
            if observed:
                hours = stats.get("observed_hours") or {}
                s.event("train", text=(
                    f"trained on {stats.get('stated_windows', 0):,} stated + "
                    f"{observed:,} observed windows "
                    f"({sum(hours.values()):,} h of recorded behaviour across "
                    f"{len(hours)} device(s))"
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

        # Anchored once, then advanced by whole simulated days. Anchoring per
        # tick would jump a day if the demo happened to run across real
        # midnight. Local midnight, never UTC: context features read
        # localtime(ts).tm_hour, and a UTC anchor shifts every predicted hour by
        # the offset -- 5:30 in IST.
        if self._midnight is None:
            lt0 = time.localtime()
            self._midnight = time.mktime(
                (lt0.tm_year, lt0.tm_mon, lt0.tm_mday, 0, 0, 0, 0, 0, -1))

        s.clock_ts = (self._midnight + self.demo_day * 86400.0
                      + hour * 3600.0 + int((self.demo_hour % 1) * 60) * 60.0)

        # Weekend from the SIMULATED date, not from whatever day it is outside.
        # The model is being asked about the day the house is living in.
        is_weekend = time.localtime(s.clock_ts).tm_wday >= 5
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
            # "held" is not a confidence band -- it says the model reached a
            # decision and was not permitted to act on it. Reporting `act` while
            # nothing moves is the screen disagreeing with the house.
            ds.gate = decided.get("gate") if decided.get("gate") == "held" else (
                "act" if ds.confidence >= 0.75 else (
                    "ask" if ds.confidence >= 0.40 else "abstain"))

        s.node_online = True
        s.automation = self.central.automation
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
                self.demo_hour += 1.0
                if self.demo_hour >= 24.0:
                    # Roll into the NEXT day rather than back onto this one.
                    # `% 24` kept the clock on a single calendar date forever, so
                    # every simulated day overwrote the previous day's hours: the
                    # usage table could never hold more than 24 distinct steps,
                    # and 24 is one short of the 25 a lag window needs. Training
                    # on observed behaviour was silently impossible.
                    self.demo_hour -= 24.0
                    self.demo_day += 1
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
            s.event("train", text="training a candidate on stated preferences + recorded behaviour")
            self.sync()
            await bcast.send(s.snapshot())
            await self.retrain_candidate(bcast)

        elif typ == "redeploy":
            await self.deploy_candidate()

        elif typ == "set_automation":
            await self._set_automation(bool(msg.get("on", True)))

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

    async def _set_automation(self, enabled: bool) -> None:
        """Hand the model its authority back, or take it away.

        Taking it away does NOT stop the system: preferences are still parsed,
        still stored, still trained on, and the lag window keeps filling with
        what the appliances actually did. Only the act of switching something
        is withheld. That is what makes turning it back on safe -- the model
        resumes warm, on a continuous window, rather than blind on a day that
        never happened.
        """
        s = self.state
        before = self.central.automation
        await self.central.set_automation(enabled)
        s.automation = self.central.automation
        s.ckpt_seq = self.central.ckpt.seq

        if before == self.central.automation:
            return

        # Mark the tiles immediately rather than letting them carry the previous
        # tick's verdict for another demo hour. The screen should not still be
        # claiming the model is acting a moment after it was told it may not.
        for st in self.central.device_states.values():
            st["gate"] = "act" if self.central.automation else "held"

        if self.central.automation:
            s.event("automation", text=(
                "automation ON - the model may act again; it kept learning while "
                "it was off, so it resumes on a warm window"
            ))
        else:
            s.event("automation", text=(
                "automation OFF - the house now does only what you tell it. "
                "The model still learns, it just does not switch anything"
            ))

    async def _speak(self, text: str) -> None:
        s = self.state
        intent = commands.parse(text)
        if intent is None:
            s.event("unparsed", text=f"could not identify a device in: {text!r}")
            return

        last = self.db.last_active_command()
        # "set the AC to 23 degrees" with no time means now. Hand the demo clock
        # over so an untimed instruction lands on this hour instead of becoming
        # a standing all-day rule.
        resolved = commands.resolve(intent, dict(last) if last else None,
                                    now_hour=int(self.demo_hour) % 24)
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
