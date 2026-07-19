"""Which dates the household treats as holidays.

`is_weekend` already tells the model that Saturday is not Tuesday. It cannot
tell it that *this particular* Tuesday is Diwali and the house will behave like
a Sunday. That is the one calendar fact the model cannot derive from a
timestamp, so it has to be supplied.

Kept as data rather than logic on purpose. Movable feasts -- Diwali, Holi, Eid,
Easter -- are lunar or computed, so no arithmetic on the date will find them,
and a household's real holidays are personal anyway: a family's own leave is
just as load-bearing here as a national one. So the built-in list covers only
India's fixed-date national holidays, and everything else is a line the user
adds.

Drop a `holidays.json` in the data directory to replace the defaults:

    ["2026-01-26", "2026-08-15", "2026-11-08"]

The file replaces rather than extends, so a household that wants only its own
dates is not stuck with ours. A missing or malformed file is not an error --
the model simply falls back to the built-ins, which is the same answer it gave
before this feature existed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# India's fixed-date national holidays. Deliberately not exhaustive: the movable
# ones cannot be derived from the date, and guessing them would put a wrong flag
# on a normal working day, which is worse than putting none on a real holiday.
DEFAULT_HOLIDAYS: frozenset[str] = frozenset({
    "01-01",   # New Year's Day
    "01-26",   # Republic Day
    "05-01",   # Labour Day
    "08-15",   # Independence Day
    "10-02",   # Gandhi Jayanti
    "12-25",   # Christmas Day
})

FILENAME = "holidays.json"

_dates: set[str] = set()          # explicit "YYYY-MM-DD" entries
_recurring: set[str] = set(DEFAULT_HOLIDAYS)   # "MM-DD", every year
_loaded_from: str | None = None


def load(data_dir: str | Path = "data") -> int:
    """Read `<data_dir>/holidays.json` if it exists. Returns the count in use.

    Entries are either "YYYY-MM-DD" for a one-off or "MM-DD" for something that
    recurs every year. Anything unparseable is skipped rather than fatal: a typo
    in one line should not take the calendar down.
    """
    global _dates, _recurring, _loaded_from

    path = Path(data_dir) / FILENAME
    if not path.exists():
        _dates, _recurring, _loaded_from = set(), set(DEFAULT_HOLIDAYS), None
        return len(_recurring)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _dates, _recurring, _loaded_from = set(), set(DEFAULT_HOLIDAYS), None
        return len(_recurring)

    if isinstance(raw, dict):                 # {"dates": [...]} is also accepted
        raw = raw.get("dates", [])
    if not isinstance(raw, list):
        _dates, _recurring, _loaded_from = set(), set(DEFAULT_HOLIDAYS), None
        return len(_recurring)

    dates, recurring = set(), set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        entry = entry.strip()
        if _valid(entry, "%Y-%m-%d"):
            dates.add(entry)
        elif _valid(entry, "%m-%d"):
            recurring.add(entry)

    _dates, _recurring, _loaded_from = dates, recurring, str(path)
    return len(_dates) + len(_recurring)


def _valid(entry: str, fmt: str) -> bool:
    try:
        time.strptime(entry, fmt)
        return True
    except ValueError:
        return False


def is_holiday(ts: float) -> bool:
    """Is the local date at `ts` a holiday?

    Reads the local date rather than UTC: a holiday is a property of the day the
    household is living in, and at 23:00 IST those are different days.
    """
    lt = time.localtime(ts)
    return (
        time.strftime("%Y-%m-%d", lt) in _dates
        or time.strftime("%m-%d", lt) in _recurring
    )


def describe() -> str:
    """One line for the boot log."""
    n = len(_dates) + len(_recurring)
    where = _loaded_from or "built-in defaults"
    return f"{n} holiday date(s) from {where}"
