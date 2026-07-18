"""Speech -> structured preference, and supersession.

Two sentence shapes:

    "set the AC to 25 degrees at 9 PM"     full command
    "change it to 23"                      follow-up -- inherits device + window

A follow-up carries no device and no time. It is resolved against the most
recent active command, so "change it to 23" means "change the 9 PM AC
preference to 23".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import devices

DAY_ALL, DAY_WEEKDAY, DAY_WEEKEND = "all", "weekday", "weekend"


@dataclass
class Intent:
    device: str | None
    on: bool
    level: float | None
    hour_start: int | None
    hour_end: int | None
    day_type: str
    spoken: str
    is_followup: bool = False


# -- vocabulary ------------------------------------------------------------

_DEVICE_WORDS: list[tuple[str, str]] = [
    (r"\bnight\s*light\b", "light.living"),
    (r"\b(light|lamp|bulb|batti)\b", "light.living"),
    (r"\b(fan|pankha)\b", "fan.bedroom"),
    (r"\b(a\.?c\.?|air\s*con\w*|cooling)\b", "ac.living"),
]

_OFF = re.compile(r"\b(turn\s+off|switch\s+off|shut\s+off|band\s+karo|bandh?\b|\boff\b)")
_FOLLOWUP = re.compile(r"\b(change|make|set)\s+(it|that|this)\b|\bisko\b|\bwahi\b")

# There is deliberately no _ON pattern. An earlier version decided "off" only if
# an off-word matched AND no on-word did, with `\bon\b` among the on-words -- so
# "turn off the AC on weekdays" matched both and came out as ON, silently
# inverting the user's instruction. "On" is the default; only an off-word moves it.

_WEEKDAY = re.compile(r"\b(weekday|weekdays|work\s*day|mon\w*\s*(to|-)\s*fri\w*)\b")
_WEEKEND = re.compile(r"\b(weekend|weekends|sat\w*\s*(and|/|&|-)?\s*sun\w*)\b")


def _find_device(low: str) -> str | None:
    for pattern, device_id in _DEVICE_WORDS:
        if re.search(pattern, low):
            return device_id
    return None


def _to_24h(hour: int, suffix: str | None) -> int:
    if suffix == "pm" and hour < 12:
        return hour + 12
    if suffix == "am" and hour == 12:
        return 0
    return hour % 24


def _find_hours(low: str) -> tuple[int | None, int | None]:
    """Returns (hour_start, hour_end), end exclusive."""
    # "from 9 to 5", "9 to 5", "between 9 and 5"
    span = re.search(
        r"\b(?:from|between)?\s*(\d{1,2})\s*(am|pm)?\s*(?:to|till|until|-|and)\s*(\d{1,2})\s*(am|pm)?",
        low,
    )
    if span:
        h0 = _to_24h(int(span.group(1)), span.group(2))
        h1_raw = int(span.group(3))
        suffix = span.group(4)
        if suffix is None and h1_raw < h0:
            # "9 to 5" means 09:00-17:00, not 09:00-05:00.
            suffix = "pm"
        h1 = _to_24h(h1_raw, suffix)
        if h1 <= h0:
            h1 = h0 + 1
        return h0, h1

    # "at 9 PM", "at 9"
    at = re.search(r"\bat\s+(\d{1,2})\s*(am|pm)?", low)
    if at:
        h = _to_24h(int(at.group(1)), at.group(2))
        return h, h + 1

    # "9 baje"
    baje = re.search(r"\b(\d{1,2})\s*baje\b", low)
    if baje:
        h = int(baje.group(1)) % 24
        return h, h + 1

    return None, None


def _find_level(low: str, device_id: str | None, on: bool) -> float | None:
    if not on or device_id is None:
        return None
    d = devices.get(device_id)

    if device_id == "light.living":
        if re.search(r"\bnight\s*light\b|\bwarm\w*\b", low):
            return d.lo
        if re.search(r"\bdaylight\b|\bbright\b|\bcool\s*white\b", low):
            return d.hi
    if device_id == "fan.bedroom" and re.search(r"\bfull\b|\bmax\w*\b|\bfast\b|\btez\b", low):
        return d.hi

    # A bare number, but only if it is not the time we already consumed.
    for match in re.finditer(r"(\d{1,4}(?:\.\d+)?)\s*(degrees?|°|percent|%|k\b|kelvin)?", low):
        value = float(match.group(1))
        unit = match.group(2)
        if unit is None:
            # Unitless numbers next to a time word are the time, not the level.
            tail = low[match.end():match.end() + 6]
            head = low[max(0, match.start() - 6):match.start()]
            if re.search(r"\bbaje\b|\s*(am|pm)\b", tail) or re.search(r"\bat\s*$", head):
                continue
        if d.lo <= value <= d.hi:
            return value
    return None


# -- parsing ---------------------------------------------------------------

def parse(text: str) -> Intent | None:
    """Structured intent, or None if no device could be identified."""
    low = " " + text.lower().strip() + " "

    device_id = _find_device(low)
    is_followup = device_id is None and bool(_FOLLOWUP.search(low))

    if device_id is None and not is_followup:
        return None

    on = not bool(_OFF.search(low))

    day_type = DAY_ALL
    if _WEEKEND.search(low):
        day_type = DAY_WEEKEND
    elif _WEEKDAY.search(low):
        day_type = DAY_WEEKDAY

    hour_start, hour_end = _find_hours(low)
    level = _find_level(low, device_id, on)

    return Intent(
        device=device_id,
        on=on,
        level=level,
        hour_start=hour_start,
        hour_end=hour_end,
        day_type=day_type,
        spoken=text.strip(),
        is_followup=is_followup,
    )


def resolve(intent: Intent, last: dict | None) -> Intent | None:
    """Fill a follow-up in from the most recent active command.

    Returns None if a follow-up has nothing to attach to -- better to ask again
    than to guess which appliance the user meant.
    """
    if not intent.is_followup and intent.device is not None:
        if intent.hour_start is None:
            intent.hour_start, intent.hour_end = 0, 24     # "all day" unless stated
        return intent

    if last is None:
        return None

    intent.device = intent.device or last["device"]
    if intent.hour_start is None:
        intent.hour_start = last["hour_start"]
        intent.hour_end = last["hour_end"]
    if intent.day_type == DAY_ALL:
        intent.day_type = last["day_type"]
    if intent.level is None:
        # Re-read the number now that we know which device it belongs to.
        intent.level = _find_level(" " + intent.spoken.lower() + " ", intent.device, intent.on)

    # "make it nicer" has the shape of a follow-up but changes nothing: no level
    # to apply and no off-switch. Acting on it would reissue the previous
    # preference as though the user had restated it. Better to ask again.
    if intent.on and intent.level is None:
        return None

    return intent


# -- supersession ----------------------------------------------------------

def day_types_overlap(a: str, b: str) -> bool:
    return a == b or DAY_ALL in (a, b)


def hours_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def overlaps(existing: dict, new: Intent) -> bool:
    """Does a stored command cover any of the same (device, day_type, hour)?"""
    return (
        existing["device"] == new.device
        and day_types_overlap(existing["day_type"], new.day_type)
        and hours_overlap(existing["hour_start"], existing["hour_end"],
                          new.hour_start, new.hour_end)
    )


# -- compiled schedule -----------------------------------------------------

def compile_schedule(active_rows) -> dict:
    """Active commands -> the node's fallback schedule.

    Shape: {device: {day_type: {"hour": [on, level]}}}. Hour keys are strings
    because this is written to the checkpoint as JSON.

    The node keeps this so it can run the house even if the model file is
    missing or its hash fails. Learning is centralised; control is not.
    """
    schedule: dict = {}
    for row in sorted(active_rows, key=lambda r: r["stated_at"]):
        device = schedule.setdefault(row["device"], {})
        by_day = device.setdefault(row["day_type"], {})
        for hour in range(row["hour_start"], row["hour_end"]):
            by_day[str(hour % 24)] = [bool(row["on_state"]), row["level"]]
    return schedule


def schedule_lookup(schedule: dict, device_id: str, hour: int,
                    is_weekend: bool) -> tuple[bool, float | None] | None:
    """Most specific day_type wins: a weekday rule beats an everyday rule."""
    by_day = schedule.get(device_id, {})
    specific = DAY_WEEKEND if is_weekend else DAY_WEEKDAY
    for day_type in (specific, DAY_ALL):
        entry = by_day.get(day_type, {}).get(str(hour % 24))
        if entry is not None:
            return bool(entry[0]), entry[1]
    return None
