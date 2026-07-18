"""
aeon/digital_twin/appliances.py

Digital Twin appliance models for ÆON Home.

Each twin maintains:
  - A current "physical" state (what the appliance is actually doing)
  - An "adaptive target" derived from ContextEngine state
  - A tick() method that steps the twin one time unit forward
  - A to_dict() method for serialisation to the WebSocket bus / API

Appliances:
  SmartACTwin     — split AC with temperature PID-like control
  SmartLightTwin  — RGB+dimmer light with circadian curve
  RobotVacuumTwin — autonomous vacuum with room path model
"""

from __future__ import annotations

import math
import time
from typing import Any


# ── SmartACTwin ──────────────────────────────────────────────────────────────

class SmartACTwin:
    """
    Digital twin for a split air-conditioner unit.

    Adaptive behaviour:
      - If occupancy > 0.4 AND temperature > comfort_max → cool to setpoint
      - If occupancy < 0.1 → eco mode (wider tolerance band, lower fan speed)
      - Nighttime → quiet mode (fan speed capped at 1)
    """

    COMFORT_SETPOINT = 24.0   # °C
    COMFORT_MAX      = 27.0   # cool if above
    COMFORT_MIN      = 21.0   # heat if below (future)
    COOL_RATE        = 0.8    # °C per tick when cooling

    def __init__(self) -> None:
        self.mode: str          = "off"         # "off" | "cool" | "eco" | "quiet"
        self.setpoint: float    = self.COMFORT_SETPOINT
        self.fan_speed: int     = 2             # 0-3
        self.current_temp: float | None = None
        self.power_w: float     = 0.0
        self.runtime_s: float   = 0.0
        self._on_since: float | None = None

    def adapt(self, ctx: dict[str, Any]) -> None:
        """Update adaptive target from context."""
        temp     = ctx.get("temperature")
        occ      = ctx.get("occupancy_score", 0.0)
        tod      = ctx.get("time_of_day", "afternoon")

        self.current_temp = temp

        if temp is None or occ < 0.05:
            self._set_mode("off")
            return

        if tod == "night":
            self.fan_speed = 1
            if temp and temp > self.COMFORT_MAX + 1:
                self._set_mode("quiet")
            else:
                self._set_mode("off")
            return

        if occ < 0.3:
            self._set_mode("eco")
            self.fan_speed = 1
        elif temp and temp > self.COMFORT_MAX:
            self._set_mode("cool")
            self.fan_speed = 3 if temp > self.COMFORT_MAX + 2 else 2
        else:
            self._set_mode("off")

    def tick(self, dt_s: float = 5.0) -> None:
        """Advance twin state by dt_s seconds."""
        if self.mode in ("cool", "quiet", "eco") and self._on_since:
            self.runtime_s += dt_s
            self.power_w = {"cool": 1200, "eco": 600, "quiet": 800}.get(self.mode, 0)
        else:
            self.power_w = 0.0

    def _set_mode(self, mode: str) -> None:
        if mode != self.mode:
            self.mode = mode
            self._on_since = time.time() if mode != "off" else None
            if mode == "off":
                self.power_w = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type":         "smart_ac",
            "mode":         self.mode,
            "setpoint":     self.setpoint,
            "fan_speed":    self.fan_speed,
            "current_temp": self.current_temp,
            "power_w":      round(self.power_w, 1),
            "runtime_s":    round(self.runtime_s, 1),
        }


# ── SmartLightTwin ───────────────────────────────────────────────────────────

# Circadian curve: (hour → (kelvin, brightness_pct))
_CIRCADIAN: dict[int, tuple[int, int]] = {
    0:  (2700,  5), 1:  (2700,  5), 2:  (2700,  5), 3:  (2700,  5),
    4:  (2700, 10), 5:  (3000, 20), 6:  (3500, 50), 7:  (4000, 80),
    8:  (5000,100), 9:  (5500,100),10:  (6000,100),11:  (6000,100),
    12: (6500,100),13:  (6500,100),14:  (6000,100),15:  (5500,100),
    16: (5000, 90),17:  (4500, 80),18:  (4000, 70),19:  (3500, 60),
    20: (3000, 50),21:  (2700, 40),22:  (2700, 20),23:  (2700, 10),
}


class SmartLightTwin:
    """
    Digital twin for a smart RGB+white light (e.g. Philips Wiz / Matter).

    Adaptive behaviour:
      - Follows circadian colour temperature curve when occupied
      - Dims / switches off when unoccupied (after grace period)
      - Scene override: "movie", "work", "sleep", "away"
    """

    UNOCCUPIED_DIM_PCT = 20
    UNOCCUPIED_TIMEOUT = 300  # s before turning off when no motion

    def __init__(self) -> None:
        self.on: bool           = False
        self.brightness: int    = 100    # 0–100 %
        self.kelvin: int        = 4000   # colour temperature
        self.rgb: tuple[int,int,int] = (255, 255, 255)
        self.scene: str         = "auto"
        self.power_w: float     = 0.0
        self._unoccupied_since: float | None = None

    def adapt(self, ctx: dict[str, Any]) -> None:
        """Update from context."""
        import datetime as dt
        occ  = ctx.get("occupancy_score", 0.0)
        tod  = ctx.get("time_of_day", "afternoon")
        hour = dt.datetime.now().hour

        if self.scene != "auto":
            return  # manual override active

        if occ > 0.15:
            self._unoccupied_since = None
            self.on = True
            k, b = _CIRCADIAN.get(hour, (4000, 100))
            self.kelvin     = k
            self.brightness = b
            self.rgb        = self._kelvin_to_rgb(k)
            self.power_w    = 9 * (b / 100)

        else:
            now = time.time()
            if self._unoccupied_since is None:
                self._unoccupied_since = now
                self.brightness = self.UNOCCUPIED_DIM_PCT
                self.power_w    = 9 * (self.UNOCCUPIED_DIM_PCT / 100)
            elif now - self._unoccupied_since > self.UNOCCUPIED_TIMEOUT:
                self.on      = False
                self.power_w = 0.0

    def set_scene(self, scene: str) -> None:
        scenes = {
            "movie":  (2200, 30),
            "work":   (6000, 100),
            "sleep":  (2700,  5),
            "away":   (None,  0),
        }
        if scene == "auto":
            self.scene = "auto"
            return
        if scene not in scenes:
            return
        k, b = scenes[scene]
        self.scene      = scene
        self.on         = b > 0
        self.brightness = b
        if k:
            self.kelvin = k
            self.rgb    = self._kelvin_to_rgb(k)
        self.power_w = 9 * (b / 100)

    @staticmethod
    def _kelvin_to_rgb(k: int) -> tuple[int, int, int]:
        """Approximate Kelvin → RGB (Tanner Helland algorithm, simplified)."""
        k = max(1000, min(40000, k)) / 100
        r = min(255, int(329.698727446 * (k - 60) ** -0.1332047592)) if k > 66 else 255
        if k <= 66:
            g = int(99.4708025861 * math.log(k) - 161.1195681661)
        else:
            g = int(288.1221695283 * (k - 60) ** -0.0755148492)
        g = max(0, min(255, g))
        b = 255 if k >= 66 else (0 if k <= 19 else int(138.5177312231 * math.log(k - 10) - 305.0447927307))
        b = max(0, min(255, b))
        return (r, g, b)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type":       "smart_light",
            "on":         self.on,
            "brightness": self.brightness,
            "kelvin":     self.kelvin,
            "rgb":        list(self.rgb),
            "scene":      self.scene,
            "power_w":    round(self.power_w, 2),
        }


# ── RobotVacuumTwin ──────────────────────────────────────────────────────────

class RobotVacuumTwin:
    """
    Digital twin for a robot vacuum (e.g. Roborock / Dreame).

    Simulates:
      - Room coverage path using a boustrophedon (lawnmower) sweep pattern
      - Battery depletion and charging cycle
      - Automatic scheduling: starts when occupancy drops to 0 at home
      - Pauses when motion detected (person home)
    """

    ROOM_W   = 10   # virtual room grid width (cells)
    ROOM_H   = 8    # virtual room grid height
    CELL_M2  = 0.25 # each cell = 0.25 m²
    FULL_BATTERY = 100
    DRAIN_PER_CELL = 0.4   # battery % per cell cleaned
    CHARGE_RATE    = 0.5   # battery % per tick when docked

    def __init__(self) -> None:
        self.state: str       = "docked"    # "docked" | "cleaning" | "paused" | "returning"
        self.battery: float   = 100.0
        self.coverage_pct: float = 0.0
        self.position: tuple[int, int] = (0, 0)
        self.path: list[tuple[int, int]] = []
        self._path_index: int  = 0
        self._schedule_enabled = True
        self._full_path = self._boustrophedon_path()

    def _boustrophedon_path(self) -> list[tuple[int, int]]:
        """Generate a lawnmower sweep path across the room grid."""
        path: list[tuple[int, int]] = []
        for row in range(self.ROOM_H):
            cols = range(self.ROOM_W) if row % 2 == 0 else range(self.ROOM_W - 1, -1, -1)
            for col in cols:
                path.append((col, row))
        return path

    def adapt(self, ctx: dict[str, Any]) -> None:
        """React to context: start cleaning when unoccupied, pause when motion."""
        occ    = ctx.get("occupancy_score", 0.0)
        motion = ctx.get("motion_active", False)

        if self.state == "cleaning" and motion:
            self.state = "paused"
            return

        if self.state == "paused" and not motion:
            self.state = "cleaning"
            return

        if self.state == "docked" and self._schedule_enabled:
            if occ < 0.05 and self.battery > 20:
                self._start_cleaning()

        if self.state == "cleaning" and self.battery < 5:
            self.state = "returning"

    def tick(self, dt_s: float = 5.0) -> None:
        """Advance vacuum state one step."""
        if self.state == "cleaning":
            if self._path_index < len(self._full_path):
                self.position = self._full_path[self._path_index]
                # Append to visible path (keep last 30 positions)
                self.path.append(self.position)
                if len(self.path) > 30:
                    self.path = self.path[-30:]
                self._path_index += 1
                self.battery = max(0, self.battery - self.DRAIN_PER_CELL)
                self.coverage_pct = min(100, (self._path_index / len(self._full_path)) * 100)
            else:
                self.state = "returning"

        elif self.state in ("docked", "returning"):
            if self.state == "returning":
                self.position = (0, 0)
                self.state    = "docked"
            self.battery = min(self.FULL_BATTERY, self.battery + self.CHARGE_RATE * dt_s)

    def _start_cleaning(self) -> None:
        self.state        = "cleaning"
        self._path_index  = 0
        self.coverage_pct = 0.0
        self.path         = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "type":         "robot_vacuum",
            "state":        self.state,
            "battery":      round(self.battery, 1),
            "coverage_pct": round(self.coverage_pct, 1),
            "position":     list(self.position),
            "path":         [list(p) for p in self.path[-15:]],
        }
