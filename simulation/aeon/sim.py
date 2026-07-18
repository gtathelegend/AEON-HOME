"""The parts of the demo that stand in for physical reality.

The node reads ambient temperature, humidity and motion for the whole zone. On
the bench there is no DHT22, so this generates a plausible day. Everything else
in the system -- transport, persistence, signing, control -- is real.
"""

from __future__ import annotations

import math

# One demo hour per this many real seconds. A whole day takes ~90 s.
SECONDS_PER_HOUR = 3.75


def ambient_at(hour: float) -> tuple[float, float]:
    """Daily temperature and humidity curve. Coolest ~05:00, hottest ~15:00."""
    phase = (hour - 15.0) / 24.0 * 2 * math.pi
    temp = 26.0 + 7.0 * math.cos(phase)
    rh = 62.0 - 1.2 * (temp - 26.0)
    return temp, rh
