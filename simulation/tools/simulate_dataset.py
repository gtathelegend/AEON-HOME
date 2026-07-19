#!/usr/bin/env python3
"""Generate a simulated history of what the house actually did.

    python tools/simulate_dataset.py --days 14
    python tools/simulate_dataset.py --days 21 --clear

There is no real house on the bench, so there is no real usage history -- and
without one, "retrain" can only ever re-learn the rules it was already given.
This writes a plausible one into the `usage` table so the retraining pipeline
has genuine observed behaviour to train on.

THE POINT IS THE DRIFT. The generated history deliberately does NOT match the
stated preferences exactly: at weekends the AC comes on an hour early and a
degree cooler, and the vacuum runs in the afternoon rather than late morning.
Those patterns exist ONLY in the observed data. A retrain that improves is
therefore learning something it was never told -- which is the whole claim the
project makes. A dataset that merely echoed the stated rules would make the
Retrain button a very expensive no-op.

This is simulated data and must be described that way. It stands in for a month
of living in the house; it is not a month of living in the house.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from aeon import commands, devices      # noqa: E402
from aeon.db import Database            # noqa: E402


def _stated(active, device_id: str, hour: int, is_weekend: bool):
    """What the stated preferences say for this hour."""
    on, level = False, None
    for row in active:
        if row["device"] != device_id:
            continue
        day_type = row["day_type"]
        if day_type == "weekday" and is_weekend:
            continue
        if day_type == "weekend" and not is_weekend:
            continue
        if row["hour_start"] <= hour < row["hour_end"]:
            on = bool(row["on_state"])
            level = row["level"] if on else None
    return on, level


def _lived(device_id: str, hour: int, is_weekend: bool, on, level, rng):
    """Bend the stated rule into what a person actually does.

    Returns (on, level, source). `source` matters: 'phone' marks a deliberate
    human correction, which is the only row that carries information the model
    was not already given.
    """
    source = "auto"

    if device_id == "ac.living" and is_weekend:
        # Weekend evenings start earlier and run cooler. Stated rule says 21-23
        # at 25 C; nobody actually waits until nine on a Saturday.
        if hour == 20:
            return True, 24.0, "phone"
        if 21 <= hour < 23:
            return True, 24.0, "phone"

    if device_id == "vacuum.home" and is_weekend:
        # Stated rule cleans at 10-12. At weekends it really happens after lunch.
        if 10 <= hour < 12:
            return False, None, "phone"
        if 15 <= hour < 17:
            return True, 70.0, "phone"

    if device_id == "fan.bedroom" and on and level is not None:
        # Small honest jitter: nobody sets exactly 70% every single day.
        level = max(0.0, min(100.0, level + rng.choice((-10.0, 0.0, 0.0, 10.0))))

    return on, level, source


def generate(db: Database, days: int, seed: int = 0) -> dict:
    rng = random.Random(seed)
    lt = time.localtime()
    midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    # Ends just before today, so it sits contiguously BEHIND whatever the running
    # hub records forward from local midnight.
    start = midnight - days * 86400

    active = db.active_commands()
    if not active:
        return {"rows": 0, "error": "no active preferences - start the hub once first"}

    rows = overrides = 0
    for day in range(days):
        for hour in range(24):
            ts = start + day * 86400 + hour * 3600
            is_weekend = time.localtime(ts).tm_wday >= 5
            occupied = devices.default_occupancy(hour)

            for device_id in devices.DEVICE_ORDER:
                on, level = _stated(active, device_id, hour, is_weekend)
                on, level, source = _lived(device_id, hour, is_weekend, on, level, rng)

                # The same occupancy rule training and runtime both use. A
                # simulated history that ignored it would teach the model to
                # fight the runtime override.
                if not occupied and devices.get(device_id).off_when_empty:
                    on, level, source = False, None, "auto"

                # Off steps carry no level, here as everywhere else.
                db.record_usage(device=device_id, on=on,
                                level=level if on else None,
                                occupied=occupied, source=source, ts=ts)
                rows += 1
                if source == "phone":
                    overrides += 1

    return {"rows": rows, "overrides": overrides, "days": days,
            "from": time.strftime("%Y-%m-%d", time.localtime(start)),
            "to": time.strftime("%Y-%m-%d", time.localtime(midnight - 3600))}


def main() -> int:
    ap = argparse.ArgumentParser(description="Simulate a usage history")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--data", default="data")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--clear", action="store_true",
                    help="delete existing usage rows first")
    args = ap.parse_args()

    path = ROOT / args.data / "aeon.db"
    if not path.exists():
        print(f"\n  no database at {path} - run `python run.py --reset` once first\n")
        return 1

    db = Database(path)
    if args.clear:
        db.conn.execute("DELETE FROM usage")
        db.conn.commit()
        print("  cleared existing usage rows")

    print(f"\n  simulating {args.days} days of behaviour into {path}")
    out = generate(db, args.days, args.seed)
    if out.get("error"):
        print(f"  {out['error']}\n")
        db.close()
        return 1

    print(f"  {out['rows']:,} usage rows written  ({out['from']} -> {out['to']})")
    print(f"  {out['overrides']:,} of them are human overrides that contradict the")
    print("  stated rules - those are the rows with something new to teach.")
    print(f"\n  total usage rows now: {len(db.usage_rows()):,}")
    print("\n  Press Retrain on the dashboard to train on it.\n")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
