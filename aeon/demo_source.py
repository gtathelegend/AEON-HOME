"""Phase 1 source: a scripted house.

This drives HubState through a plausible day so the dashboard can be built and
judged against live data before the real backend exists. Everything here is
replaced in Phase 2 by the real central node -- the contract it honours is
`state` / `run()` / `on_message()`, nothing more.

What is real here: the state shape, the fan-out ordering (leaf first, PC second),
the confidence gate, the occupancy override, and the measured hop timings.
What is simulated: the model itself (a hand-written policy stands in for ONNX
inference) and the sensor feed.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time

from . import devices, protocol, sim
from .hubstate import HubState

SECONDS_PER_HOUR = sim.SECONDS_PER_HOUR
ambient_at = sim.ambient_at


class ScriptedPolicy:
    """Stands in for the deployed ONNX model until Phase 3.

    Returns (on, level, confidence) per device. The shapes match what the trained
    model is expected to learn: the AC follows stated preference and hour, the fan
    follows ambient temperature, the light follows time of day.
    """

    def __init__(self) -> None:
        # Stated preferences: device -> list of (hour_start, hour_end, on, level)
        self.preferences: dict[str, list[tuple[int, int, bool, float | None]]] = {
            "ac.living": [(21, 23, True, 25.0)],
        }

    def state_for(self, device_id: str, hour: int, temp_c: float) -> tuple[bool, float | None, float]:
        for h0, h1, on, level in self.preferences.get(device_id, []):
            if h0 <= hour < h1:
                return on, level, 0.97

        if device_id == "ac.living":
            return False, None, 0.88

        if device_id == "fan.bedroom":
            if temp_c < 24.0:
                return False, None, 0.91
            speed = max(0.0, min(100.0, (temp_c - 23.0) / 7.0 * 100.0))
            return True, round(speed), 0.93

        if device_id == "light.living":
            if 7 <= hour < 18:
                return True, 6479.0, 0.95          # daylight
            if 18 <= hour < 23:
                return True, 3000.0, 0.92          # warm evening
            if hour == 23:
                return True, 2207.0, 0.96          # night light
            return False, None, 0.90

        return False, None, 0.0


class ScriptedHouse:
    """Phase 1 stand-in for the central node."""

    def __init__(self) -> None:
        self.state = HubState()
        self.policy = ScriptedPolicy()
        self.demo_hour = 8.0
        self.paused = False
        self.leaf_offline: set[str] = set()
        self._boot()

    # -- boot -------------------------------------------------------------

    def _boot(self) -> None:
        s = self.state
        t0 = time.perf_counter()
        s.node_online = True
        s.link = "connected"
        s.ckpt_seq = 214
        s.restore_ms = (time.perf_counter() - t0) * 1000 + 0.3
        s.policy.model_v = 1
        s.policy.cv_auc = 1.0
        s.policy.level_mae = {"ac.living": 0.0, "fan.bedroom": 0.215, "light.living": 12.3}
        s.policy.n_windows = 1944
        s.policy.params = 6850
        s.policy.size_bytes = 9835
        s.policy.kind = "int8 ONNX"
        s.policy.sha256 = hashlib.sha256(b"aeon_ts.onnx.v1").hexdigest()
        s.policy.train_seconds = 2.99
        s.policy.trained_at = time.time()
        self._refresh_learned_week()
        s.event("boot", text="checkpoint restored, seq 214, model v1 loaded")

    def _refresh_learned_week(self) -> None:
        rows = []
        for device_id, prefs in self.policy.preferences.items():
            d = devices.get(device_id)
            for h0, h1, on, level in prefs:
                what = d.format_level(level) if on else "off"
                rows.append({
                    "device": device_id,
                    "label": d.label,
                    "text": f"Daily {h0:02d}-{h1:02d}  {what}",
                })
        for device_id in devices.DEVICE_ORDER:
            if device_id not in self.policy.preferences:
                d = devices.get(device_id)
                rows.append({
                    "device": device_id,
                    "label": d.label,
                    "text": f"Follows {d.learned_from}",
                })
        rows.append({"device": "*", "label": "ALL", "text": "Off when the room is empty"})
        self.state.learned_week = rows

    # -- the control tick -------------------------------------------------

    def tick(self) -> None:
        s = self.state
        hour_i = int(self.demo_hour) % 24
        temp, rh = ambient_at(self.demo_hour)

        s.clock_ts = time.mktime(time.localtime()[:3] + (hour_i, int((self.demo_hour % 1) * 60), 0, 0, 0, -1))
        s.temp_c, s.rh_pct = temp, rh
        s.occupied = devices.default_occupancy(hour_i)
        s.motion = 1 if s.occupied else 0

        for device_id in devices.DEVICE_ORDER:
            on, level, conf = self.policy.state_for(device_id, hour_i, temp)

            # Occupancy overrides the model, and is applied AFTER inference.
            # "Nobody is home" should never be a probabilistic judgement.
            if not s.occupied and devices.get(device_id).off_when_empty:
                on, level = False, None

            gate = "act" if conf >= 0.75 else ("ask" if conf >= 0.40 else "abstain")
            if gate != "act":
                continue

            ds = s.devices[device_id]
            if ds.on == on and ds.level == level and ds.source == "model":
                continue
            if device_id in self.leaf_offline:
                ds.online = False
                continue

            ds.online = True
            s.apply_leaf_ack(device_id, on, level, source="model", confidence=conf, gate=gate)
            s.local_packets += 2

    # -- phone command fan-out --------------------------------------------

    def handle_command(self, device_id: str, on: bool, level: float | None,
                       spoken: str, hour: int | None = None) -> dict:
        """A command from the phone always goes to two places.

        Order matters: the leaf first, because a person is standing there waiting
        for the appliance; the PC second, because that is what turns the sentence
        into training data. Neither failure is allowed to break the other.
        """
        s = self.state
        msg = protocol.command(device_id, on, level, spoken)

        if not protocol.verify(msg):
            return s.event("rejected", device=device_id, reason="bad signature")

        # 1 -> leaf: actuate now
        t0 = time.perf_counter()
        if device_id in self.leaf_offline:
            leaf = {"status": "offline", "ms": None, "applied": None}
            s.devices[device_id].online = False
        else:
            s.apply_leaf_ack(device_id, on, level, source="phone", confidence=1.0, gate="act")
            s.devices[device_id].online = True
            leaf = {
                # 4 dp, not 2: these hops land in single-digit microseconds, and
                # rounding to 0.01 ms throws away the number the dashboard is
                # there to show.
                "status": "leaf_ack",
                "ms": round((time.perf_counter() - t0) * 1000, 4),
                "applied": on,
                "level": level,
            }

        # 2 -> PC: the preference becomes training data
        t1 = time.perf_counter()
        if s.pc_reachable:
            # Measure AFTER the record lands, not before. Stopping the clock on
            # the line above timed dict construction and reported "0 us" for
            # work that had not happened yet.
            #
            # Learn at the hour the user *stated*, not the hour they happened to
            # speak. "Set the AC to 25 at 9 PM" said at 10 AM programs 9 PM.
            self._learn(device_id, on, level, hour)
            pc = {"status": "delivered", "ms": round((time.perf_counter() - t1) * 1000, 4)}
        else:
            s.spooled += 1
            pc = {"status": "spooled", "ms": None, "queued": s.spooled}

        s.local_packets += 3
        return s.event(
            "fanout",
            device=device_id,
            label=devices.get(device_id).label,
            spoken=spoken,
            leaf=leaf,
            pc=pc,
        )

    def _learn(self, device_id: str, on: bool, level: float | None, hour: int | None = None) -> None:
        """Fold a stated preference into the policy, superseding any overlap.

        Supersession, not append. Say "25 at 9 PM" then "23 at 9 PM" and storing
        both would train the model on 24 -- the average of two things, one of
        which the user explicitly retracted.
        """
        h = int(self.demo_hour) % 24 if hour is None else hour % 24
        prefs = self.policy.preferences.setdefault(device_id, [])
        prefs[:] = [p for p in prefs if not (p[0] <= h < p[1])]
        prefs.append((h, h + 1, on, level))
        self._refresh_learned_week()

    # -- speech -> intent (Phase 1: regex. Phase 2: commands.py) ----------

    _DEVICE_WORDS = {
        "ac": "ac.living", "a.c": "ac.living", "air": "ac.living", "cool": "ac.living",
        "fan": "fan.bedroom",
        "light": "light.living", "lamp": "light.living", "bulb": "light.living",
    }

    def parse(self, text: str) -> dict | None:
        low = text.lower()

        device_id = None
        for word, did in self._DEVICE_WORDS.items():
            if word in low:
                device_id = did
                break
        if device_id is None:
            return None

        on = not re.search(r"\b(turn off|switch off|off\b|band karo)", low)

        level = None
        num = re.search(r"(\d+(?:\.\d+)?)\s*(?:degree|degrees|°|percent|%|k\b|kelvin)?", low)
        if num:
            value = float(num.group(1))
            d = devices.get(device_id)
            if d.lo <= value <= d.hi:
                level = value
            elif device_id == "fan.bedroom" and "full" not in low:
                level = max(d.lo, min(d.hi, value))
        if "full" in low or "max" in low:
            level = devices.get(device_id).hi
        if level is None and on:
            level = devices.get(device_id).hi if device_id == "fan.bedroom" else None

        hour = None
        at = re.search(r"\bat\s+(\d{1,2})\s*(am|pm)?", low) or re.search(r"(\d{1,2})\s*baje", low)
        if at:
            hour = int(at.group(1))
            suffix = at.group(2) if at.lastindex and at.lastindex >= 2 else None
            if suffix == "pm" and hour < 12:
                hour += 12
            if suffix == "am" and hour == 12:
                hour = 0

        return {"device": device_id, "on": on, "level": level, "hour": hour, "spoken": text}

    # -- source contract ---------------------------------------------------

    async def run(self, bcast) -> None:
        while True:
            if not self.paused:
                self.demo_hour = (self.demo_hour + 1.0) % 24
                self.tick()
            await bcast.send(self.state.snapshot())
            await asyncio.sleep(SECONDS_PER_HOUR)

    async def on_message(self, msg: dict, bcast) -> None:
        typ = msg.get("typ")
        s = self.state

        if typ == "speak":
            intent = self.parse(msg.get("text", ""))
            if intent is None:
                s.event("unparsed", text=msg.get("text", ""))
            else:
                self.handle_command(intent["device"], intent["on"], intent["level"],
                                    intent["spoken"], intent["hour"])

        elif typ == "command":
            self.handle_command(
                msg["device"], bool(msg.get("on")), msg.get("level"),
                msg.get("spoken", "manual control"),
            )

        elif typ == "retrain":
            await self._retrain(bcast)

        elif typ == "toggle_pc":
            s.pc_reachable = not s.pc_reachable
            if s.pc_reachable and s.spooled:
                s.event("flush", text=f"reconnected, flushed {s.spooled} spooled record(s)")
                s.spooled = 0
            else:
                s.event("link", text=f"PC {'reachable' if s.pc_reachable else 'unreachable'}")

        elif typ == "toggle_leaf":
            device_id = msg["device"]
            if device_id in self.leaf_offline:
                self.leaf_offline.discard(device_id)
                s.devices[device_id].online = True
            else:
                self.leaf_offline.add(device_id)
                s.devices[device_id].online = False
            s.event("leaf_link", device=device_id,
                    text=f"{devices.get(device_id).label} {'offline' if device_id in self.leaf_offline else 'online'}")

        elif typ == "attack":
            # An unsigned command, and one tampered with after signing.
            forged = protocol.command("fan.bedroom", True, 100.0, "forged")
            if msg.get("mode") == "tampered":
                forged["level"] = 100.0
                forged["device"] = "ac.living"
            else:
                forged.pop("sig", None)
            ok = protocol.verify(forged)
            s.event("rejected" if not ok else "accepted",
                    device=forged.get("device"),
                    reason="bad signature" if not ok else "verified",
                    text=f"{msg.get('mode', 'unsigned')} command from the same WiFi")

        elif typ == "pause":
            self.paused = not self.paused
            s.event("clock", text=f"demo clock {'paused' if self.paused else 'running'}")

        elif typ == "settime":
            self.demo_hour = float(msg.get("hour", 9)) % 24
            self.tick()

        await bcast.send(s.snapshot())

    async def _retrain(self, bcast) -> None:
        s = self.state
        s.event("train", text="retraining on all devices' active preferences")
        await bcast.send(s.snapshot())
        await asyncio.sleep(1.2)

        s.policy.model_v += 1
        s.policy.n_windows = 1944 + s.policy.model_v * 24
        s.policy.train_seconds = 2.99
        s.policy.sha256 = hashlib.sha256(f"aeon_ts.onnx.v{s.policy.model_v}".encode()).hexdigest()
        s.policy.trained_at = time.time()
        s.ckpt_seq += 1
        s.event("deploy", text=(
            f"{s.policy.size_bytes:,} B -> hash verified -> ack v{s.policy.model_v}, "
            f"warm-start 24 steps x {len(devices.DEVICE_ORDER)} devices; leaves received nothing"
        ))
