"""Device registry.

Level ranges travel with the model, and the central node denormalises per device
from the same numbers the PC trained on. DEVICE_ORDER is baked into the deployed
model's input layout: appending a device is safe, reordering silently corrupts
every prediction.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    id: str
    label: str
    level_name: str          # what the level means for this device
    unit: str
    lo: float                # bottom of the level range
    hi: float                # top of the level range
    driver: str              # how the leaf switches the load
    learned_from: str        # what drives this device's level
    off_when_empty: bool = True

    def normalise(self, level: float) -> float:
        """Level in its own unit -> [-1, 1]."""
        span = self.hi - self.lo
        return 2.0 * (level - self.lo) / span - 1.0

    def denormalise(self, z: float) -> float:
        """[-1, 1] -> level in its own unit, clamped to the device's range."""
        span = self.hi - self.lo
        level = (z + 1.0) / 2.0 * span + self.lo
        return max(self.lo, min(self.hi, level))

    def format_level(self, level: float | None) -> str:
        if level is None:
            return "--"
        if self.unit == "K":
            return f"{level:.0f}K"
        if self.unit == "%":
            return f"{level:.0f}%"
        return f"{level:.1f}{self.unit}"

    def format_error(self, value: float) -> str:
        """Format an error term (MAE) in this device's own unit.

        Reported per device rather than as one normalised number, because 0.1
        is a tenth of a degree for the AC and 200 kelvin for the light. Carries
        more precision than format_level: rounding 0.215 % to "0 %" throws away
        the only thing the number was there to say.
        """
        if self.unit == "K":
            return f"{value:.1f}K"
        if self.unit == "%":
            return f"{value:.3f}%"
        return f"{value:.2f}{self.unit}"


# Fixed. Baked into the deployed model's device one-hot. The vacuum was appended
# rather than slotted in alphabetically: appending shifts no existing index, so
# every previously trained one-hot still means what it meant.
DEVICE_ORDER = ["ac.living", "fan.bedroom", "light.living", "vacuum.home"]

REGISTRY: dict[str, Device] = {
    "ac.living": Device(
        id="ac.living",
        label="AC LIVING",
        level_name="setpoint",
        unit="°C",
        lo=16.0,
        hi=30.0,
        driver="relay/IR",
        learned_from="stated preference + hour",
    ),
    "fan.bedroom": Device(
        id="fan.bedroom",
        label="FAN BEDROOM",
        level_name="speed",
        unit="%",
        lo=0.0,
        hi=100.0,
        driver="relay",
        learned_from="ambient temperature",
    ),
    "light.living": Device(
        id="light.living",
        label="LIGHT LIVING",
        level_name="colour",
        unit="K",
        lo=2200.0,
        hi=6500.0,
        driver="driver",
        learned_from="hour of day",
    ),
    # The one device an empty room does not switch off. The other three exist to
    # serve someone who is present; a vacuum is the opposite -- an empty room is
    # the good time to run, not a reason to stop.
    #
    # It is not gated to run ONLY when empty either, which would be the tidier
    # story: default_occupancy() calls 07:00-23:00 occupied, so an empty-only
    # vacuum could never honour "clean at 3 PM" -- it would accept the sentence,
    # learn it, and then silently never act on it. Time preference decides, and
    # occupancy stays out of the way.
    "vacuum.home": Device(
        id="vacuum.home",
        label="VACUUM HOME",
        level_name="suction",
        unit="%",
        lo=0.0,
        hi=100.0,
        driver="BLE/dock relay",
        learned_from="stated preference + hour",
        off_when_empty=False,
    ),
}


def get(device_id: str) -> Device:
    try:
        return REGISTRY[device_id]
    except KeyError:
        raise KeyError(f"unknown device {device_id!r}; known: {DEVICE_ORDER}") from None


def one_hot(device_id: str) -> list[float]:
    """Device one-hot appended to every training window and model input."""
    return [1.0 if d == device_id else 0.0 for d in DEVICE_ORDER]


def default_occupancy(hour: int) -> bool:
    """The single occupancy definition.

    Training synthesis and the runtime must agree. They disagreed once -- training
    assumed "occupied if hour >= 7" while the runtime claimed occupied at 3 AM --
    and predictions collapsed while every individual value still looked plausible.
    Both call this now.
    """
    return 7 <= hour <= 23


def occupancy_rule_label() -> str:
    """Who the "off when the room is empty" rule actually covers.

    Derived, not written down. The caption used to read ALL, which stopped being
    true the moment a device opted out -- and a dashboard that says ALL while a
    vacuum tile sits above it running in an empty house is telling the room
    something false about the very thing it is showing.
    """
    covered = [d for d in DEVICE_ORDER if REGISTRY[d].off_when_empty]
    if len(covered) == len(DEVICE_ORDER):
        return "ALL"
    return " · ".join(REGISTRY[d].label.split()[0] for d in covered)


def level_ranges() -> dict[str, list[float]]:
    """Shipped in the deploy manifest so the node denormalises exactly as the PC did."""
    return {d: [REGISTRY[d].lo, REGISTRY[d].hi] for d in DEVICE_ORDER}
