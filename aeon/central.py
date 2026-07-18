"""The central node -- Arduino UNO Q.

Holds the policy, runs every decision, routes every command. It does not switch
loads directly; leaves do that. The central node decides, the leaves act.

It is the one device that cannot be switched off, which is the honest cost of
centralising inference: if it dies the house stops adapting. That is the right
trade, because the alternative -- an NPU in every light switch -- is not a
product anyone would buy.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

from . import checkpoint, commands, devices, protocol, sequence, tsmodel
from .runner import NodeRunner
from .sequence import SequenceBuffer, Step
from .wifi_link import WifiLink

CHECKPOINT_INTERVAL = 30.0     # seconds; plus every significant event


class CentralNode:
    def __init__(self, ckpt_path: str | Path, spool_path: str | Path,
                 model_path: str | Path, pc_host: str = "127.0.0.1",
                 pc_port: int = 0) -> None:
        self.ckpt_path = Path(ckpt_path)
        self.model_path = Path(model_path)
        self.link = WifiLink(pc_host, pc_port, spool_path)

        self.leaves: dict[str, tuple[str, int]] = {}
        self._conns: dict[str, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}

        self.ckpt = checkpoint.Checkpoint()
        self.schedule: dict = {}
        self.device_states: dict[str, dict] = {
            d: {"on": False, "level": None, "src": "idle", "confidence": 0.0}
            for d in devices.DEVICE_ORDER
        }

        # The model, and one lag window per device. The node is the only device
        # in the house that holds a model.
        self.runner: NodeRunner | None = None
        self.buffers: dict[str, SequenceBuffer] = {
            d: SequenceBuffer(d) for d in devices.DEVICE_ORDER
        }
        # The last trained day, indexed by hour, per device. Used to re-seed an
        # in-distribution window whenever the live one is not time-aligned.
        self.warm_day: dict[str, list] = {}
        self.inference_us = 0.0
        self.last_tick_ts = time.time()

        self.restore_ms = 0.0
        self.restore_from = "none"
        self.last_save_ms = 0.0
        self._last_save_at = 0.0
        self.local_packets = 0
        self.occupied = False        # last known, so usage rows carry it
        self._bg: set[asyncio.Task] = set()

    # -- wiring ------------------------------------------------------------

    def register_leaf(self, device_id: str, host: str, port: int) -> None:
        self.leaves[device_id] = (host, port)

    def set_pc(self, host: str, port: int) -> None:
        self.link.host, self.link.port = host, port

    # -- boot / restore ----------------------------------------------------

    async def restore(self) -> bool:
        """1. read state.ckpt  2. valid -> resume  3. else previous generations
        4. all fail -> safe defaults (everything off, ask before acting).

        eMMC restore is sub-millisecond; WiFi association takes seconds. The node
        resumes *controlling* instantly and resumes *learning* when the network
        returns -- worth reporting separately rather than as one "ready".
        """
        ckpt, ms, provenance = checkpoint.load(self.ckpt_path)
        self.restore_ms, self.restore_from = ms, provenance

        if ckpt is None:
            self.ckpt = checkpoint.Checkpoint()
            return False

        self.ckpt = ckpt
        self.schedule = ckpt.schedule or {}
        for device_id, state in (ckpt.device_states or {}).items():
            if device_id in self.device_states:
                self.device_states[device_id].update(state)

        # Restore the lag windows. Without them a restart leaves the model blind
        # to recent history: the first prediction drifts and keeps drifting
        # until a full day of context rebuilds.
        for device_id in devices.DEVICE_ORDER:
            self.buffers[device_id] = SequenceBuffer.from_state(
                device_id, (ckpt.seq_buffer or {}).get(device_id)
            )

        # Reload the model from eMMC, but only if it still matches the hash the
        # checkpoint recorded. A file that changed underneath us is not the
        # model that was validated.
        if self.model_path.exists() and ckpt.model_sha256:
            blob = self.model_path.read_bytes()
            if hashlib.sha256(blob).hexdigest() == ckpt.model_sha256:
                try:
                    self.runner = NodeRunner(blob)
                except Exception:
                    self.runner = None      # fall back to the compiled schedule
        return True

    async def save(self, reason: str = "interval") -> float:
        self.ckpt.seq += 1
        self.ckpt.schedule = self.schedule
        self.ckpt.device_states = self.device_states
        self.ckpt.seq_buffer = {d: b.to_state() for d, b in self.buffers.items()}
        self.ckpt.spool_offset = self.link.spool_count()
        self.last_save_ms = checkpoint.save(self.ckpt_path, self.ckpt)
        self._last_save_at = time.monotonic()
        return self.last_save_ms

    async def maybe_save(self) -> None:
        if time.monotonic() - self._last_save_at >= CHECKPOINT_INTERVAL:
            await self.save("interval")

    # -- leaf transport ----------------------------------------------------

    def _drop_leaf(self, device_id: str) -> None:
        conn = self._conns.pop(device_id, None)
        if conn is not None:
            try:
                conn[1].close()
            except Exception:
                pass

    async def _leaf_rpc(self, device_id: str, msg: dict, timeout: float = 2.0) -> dict | None:
        """One signed round trip. Retries once, because a leaf that rebooted
        leaves a dead socket that looks identical to a leaf that is gone."""
        if device_id not in self.leaves:
            return None

        for attempt in (1, 2):
            if device_id not in self._conns:
                host, port = self.leaves[device_id]
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port), timeout)
                    self._conns[device_id] = (reader, writer)
                except (OSError, asyncio.TimeoutError):
                    return None

            reader, writer = self._conns[device_id]
            try:
                writer.write(json.dumps(msg).encode() + b"\n")
                await asyncio.wait_for(writer.drain(), timeout)
                line = await asyncio.wait_for(reader.readline(), timeout)
                if not line:
                    raise ConnectionError("leaf closed the connection")
                self.local_packets += 2
                return json.loads(line)
            except (OSError, asyncio.TimeoutError, ConnectionError, json.JSONDecodeError):
                self._drop_leaf(device_id)
                if attempt == 2:
                    return None
        return None

    async def connect_leaves(self) -> int:
        """Open every leaf socket at boot.

        Without this the first spoken command pays TCP connection setup -- a few
        milliseconds instead of a few microseconds -- and that cost lands on the
        person standing in front of the appliance waiting for it.
        """
        connected = 0
        for device_id, (host, port) in self.leaves.items():
            if device_id in self._conns:
                connected += 1
                continue
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=2.0)
                self._conns[device_id] = (reader, writer)
                connected += 1
            except (OSError, asyncio.TimeoutError):
                pass
        return connected

    async def actuate(self, device_id: str, on: bool, level: float | None,
                      src: str) -> dict | None:
        msg = protocol.actuate(device_id, on, level, src)
        ack = await self._leaf_rpc(device_id, msg)
        if ack and ack.get("typ") == "leaf_ack" and protocol.verify(ack):
            self.device_states[device_id] = {
                "on": bool(ack["on"]), "level": ack["level"],
                "src": src, "confidence": 1.0 if src == "phone" else 0.9,
            }
            if ack.get("changed"):
                self._emit_usage(device_id, bool(ack["on"]), ack["level"], src)
        return ack

    def _emit_usage(self, device_id: str, on: bool, level: float | None,
                    src: str) -> None:
        """Record what the appliance did -- off the critical path.

        This must never be awaited inside the leaf hop. Awaiting it there put a
        PC round trip inside the measured leaf latency (0.7 ms -> 2 ms) and,
        far worse, made actuating an appliance depend on the PC being reachable.
        The whole point of the fan-out is that neither failure breaks the other.
        """
        token = protocol.usage(device=device_id, on=on, level=level,
                               occupied=self.occupied, src=src, ts=time.time())
        task = asyncio.create_task(self.link.send(token))
        self._bg.add(task)                      # hold a reference; bare tasks get GC'd
        task.add_done_callback(self._bg.discard)

    # -- the fan-out rule --------------------------------------------------

    async def handle_command(self, msg: dict) -> dict:
        """A command from the phone always goes to two places.

        The leaf first, because a person is standing there waiting for the
        appliance. The PC second, because that is what turns the sentence into
        training data. Neither failure is allowed to break the other.
        """
        if not protocol.verify(msg):
            return {"kind": "rejected", "reason": "bad signature",
                    "device": msg.get("device")}

        device_id = msg["device"]
        on, level = bool(msg["on"]), msg.get("level")

        # 1 -> leaf
        t0 = time.perf_counter()
        ack = await self.actuate(device_id, on, level, src="phone")
        leaf_ms = (time.perf_counter() - t0) * 1000
        if ack is None:
            leaf = {"status": "offline", "ms": None}
        elif ack.get("status") == "rejected":
            leaf = {"status": "rejected", "ms": round(leaf_ms, 4),
                    "reason": ack.get("reason")}
        else:
            leaf = {"status": "leaf_ack", "ms": round(leaf_ms, 4),
                    "applied": bool(ack["on"]), "level": ack["level"],
                    "changed": ack.get("changed")}

        # 2 -> PC
        t1 = time.perf_counter()
        pref = protocol.preference(
            device=device_id, on=on, level=level, spoken=msg.get("spoken", ""),
            ts=msg.get("ts", time.time()),
            hour_start=int(msg.get("hour_start", 0)),
            hour_end=int(msg.get("hour_end", 24)),
            day_type=msg.get("day_type", commands.DAY_ALL),
        )
        status = await self.link.send(pref)
        pc_ms = (time.perf_counter() - t1) * 1000
        pc = ({"status": "delivered", "ms": round(pc_ms, 4)} if status == "delivered"
              else {"status": "spooled", "ms": None, "queued": self.link.spool_count()})

        await self.save("command")
        return {"kind": "fanout", "device": device_id, "leaf": leaf, "pc": pc,
                "spoken": msg.get("spoken", "")}

    # -- the control tick --------------------------------------------------

    def _infer(self, device_id: str, ts: float, ambient: float) -> tuple[bool, float | None, float, str]:
        """One decision for one device. Returns (on, level, confidence, source)."""
        spec = devices.get(device_id)

        if self.runner is not None:
            self._ensure_aligned(device_id, ts)
            buffer = self.buffers[device_id]
            x = buffer.model_input(ts, ambient, self.ckpt.ambient_mean,
                                   self.ckpt.ambient_std)
            p_on, level_z = self.runner.run(x)
            self.inference_us = self.runner.last_us

            on = p_on >= 0.5
            level = spec.denormalise(level_z) if on else None
            score = tsmodel.confidence(p_on, warm=buffer.warm)
            return on, level, score, "model"

        # No model loaded: run the compiled fallback so the house keeps working.
        lt = time.localtime(ts)
        entry = commands.schedule_lookup(self.schedule, device_id, lt.tm_hour,
                                         lt.tm_wday >= 5)
        if entry is None:
            return False, None, 0.80, "schedule"
        on, level = entry
        return on, level, 0.95, "schedule"

    async def tick(self, hour: int, is_weekend: bool, ambient: float,
                   occupied: bool, ts: float | None = None) -> list[dict]:
        """Decide, then actuate what changed. Runs with no PC involved."""
        self.occupied = occupied
        now = ts if ts is not None else time.time()
        self.last_tick_ts = now
        changes = []

        for device_id in devices.DEVICE_ORDER:
            on, level, score, source = self._infer(device_id, now, ambient)
            decision = tsmodel.gate(score)

            # Occupancy overrides the model, and is applied AFTER inference.
            # "Nobody is home" should never be a probabilistic judgement.
            if not occupied and devices.get(device_id).off_when_empty:
                on, level = False, None
                decision = "act"

            current = self.device_states[device_id]
            if decision == "act" and not (current["on"] == on and current["level"] == level):
                ack = await self.actuate(device_id, on, level, src=source)
                if ack is not None and ack.get("typ") == "leaf_ack":
                    changes.append({"device": device_id, "on": on, "level": level})
            self.device_states[device_id]["confidence"] = score
            self.device_states[device_id]["gate"] = decision

            # Push the APPLIED state back into the window -- what the appliance
            # actually did, not what the model wished for. An off step records
            # no level; writing the model's raw output there poisons the window
            # and the input drifts off-distribution within a day.
            applied = self.device_states[device_id]
            self.buffers[device_id].push(Step(
                on=bool(applied["on"]),
                level=applied["level"] if applied["on"] else None,
                occupied=occupied,
                ambient_c=ambient,
                ts=now,
            ))

        await self.maybe_save()
        return changes

    async def send_telemetry(self, temp_c: float, rh_pct: float, motion: int,
                             ts: float) -> str:
        token = protocol.telemetry(
            temp_c=temp_c, rh_pct=rh_pct, motion=motion,
            device_states={d: {"on": s["on"], "level": s["level"]}
                           for d, s in self.device_states.items()},
            model_v=self.ckpt.model_v, ts=ts,
        )
        return await self.link.send(token)

    # -- deployment --------------------------------------------------------

    async def apply_deployment(self, manifest: dict, blob: bytes) -> dict:
        """Verify, persist, load, ack. A truncated transfer must never become
        a live policy."""
        if not protocol.verify(manifest):
            return protocol.reject("bad signature")

        if hashlib.sha256(blob).hexdigest() != manifest["sha256"]:
            return protocol.reject("sha256 mismatch")

        # A reordered one-hot would silently corrupt every prediction, so a
        # mismatch is rejected outright rather than tolerated.
        if manifest.get("device_order") != devices.DEVICE_ORDER:
            return protocol.reject("device_order mismatch")

        kind = manifest.get("kind", "schedule")

        # The input layout is baked into the deployed weights. A model built for
        # a different window or feature count would still load and still return
        # numbers -- wrong ones.
        if kind != "schedule":
            if manifest.get("window") not in (None, sequence.WINDOW):
                return protocol.reject("window mismatch")
            if manifest.get("input_dim") not in (None, sequence.INPUT_DIM):
                return protocol.reject("input_dim mismatch")

        # Durable-replace the artefact itself, then swap it in.
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.model_path.with_suffix(self.model_path.suffix + ".tmp")
        tmp.write_bytes(blob)
        tmp.replace(self.model_path)

        previous_runner = self.runner
        previous_schedule = self.schedule
        try:
            if kind == "schedule":
                self.schedule = json.loads(blob)
                self.runner = None
            else:
                self.runner = NodeRunner(blob)
                # The fallback schedule rides along in the manifest so the node
                # can still run the house if the model is ever unloadable.
                if isinstance(manifest.get("schedule"), dict):
                    self.schedule = manifest["schedule"]

            self.ckpt.model_v = manifest["model_v"]
            self.ckpt.model_sha256 = manifest["sha256"]
            self.ckpt.ambient_mean = manifest.get("ambient_mean", 28.0)
            self.ckpt.ambient_std = manifest.get("ambient_std", 8.0)

            self._seed_warm_start(manifest.get("warm_start"), now=self.last_tick_ts)
            await self.save("deploy")
        except Exception as exc:
            # On failure fall back to the previous model rather than leaving the
            # house with nothing driving it.
            self.runner = previous_runner
            self.schedule = previous_schedule
            return protocol.reject(f"load failed: {exc}")

        return {"status": "ok", "model_v": manifest["model_v"],
                "bytes": len(blob), "devices": devices.DEVICE_ORDER,
                "kind": kind, "warm_started": bool(manifest.get("warm_start"))}

    def _seed_warm_start(self, warm_start: dict | None, now: float | None = None) -> None:
        """Start the model in distribution, and aligned to the current hour.

        An autoregressive model reads its own recent output, and a freshly
        deployed node has an all-off window -- a history the model never saw in
        training. Worse, it is self-fulfilling: it predicts off, records off,
        and never bootstraps into the pattern. This was a real failure in
        development; every device sat permanently off despite CV AUC 1.0.

        So the model ships with the last trained day indexed by hour, and the
        node rotates it to end at the hour before now.
        """
        if not isinstance(warm_start, dict):
            return
        self.warm_day = warm_start
        for device_id in devices.DEVICE_ORDER:
            self._reseed(device_id, now if now is not None else time.time())

    def _reseed(self, device_id: str, now_ts: float) -> bool:
        """Rebuild this device's window from the trained day, ending at now-1h."""
        by_hour = (self.warm_day or {}).get(device_id)
        if not by_hour:
            return False

        steps: list[Step] = []
        for back in range(sequence.WINDOW, 0, -1):
            ts = now_ts - back * 3600
            row = by_hour[time.localtime(ts).tm_hour]
            if row is None:
                continue
            steps.append(Step(bool(row[0]), row[1], bool(row[2]), float(row[3]), ts))

        if len(steps) < sequence.WINDOW:
            return False
        self.buffers[device_id] = SequenceBuffer(device_id, steps)
        return True

    def _ensure_aligned(self, device_id: str, now_ts: float) -> None:
        """window[-1] must be the step immediately before the one being predicted.

        A cold boot, a missed tick or a jumped demo clock all leave the window
        pointing at the wrong hour, and the model then answers confidently about
        a day that is not today. Re-seed from the trained day rather than
        predict from a misaligned history.
        """
        buffer = self.buffers[device_id]
        try:
            buffer.check_alignment(now_ts)
            if buffer.warm:
                return
        except sequence.AlignmentError:
            pass
        self._reseed(device_id, now_ts)

    # -- shutdown ----------------------------------------------------------

    async def close(self) -> None:
        for task in list(self._bg):
            task.cancel()
        for device_id in list(self._conns):
            self._drop_leaf(device_id)
        await self.link.close()
