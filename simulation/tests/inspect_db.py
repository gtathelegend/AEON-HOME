#!/usr/bin/env python3
"""Show what actually persisted. Run after driving the hub.

    python tests/inspect_db.py [path/to/aeon.db]
"""

import sqlite3
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/aeon.db")
if not path.exists():
    print(f"no database at {path}")
    raise SystemExit(1)

conn = sqlite3.connect(str(path))
conn.row_factory = sqlite3.Row

print(f"\n  {path}\n")

print("  ACTIVE PREFERENCES")
for r in conn.execute(
        "SELECT device, on_state, level, hour_start, hour_end, day_type, source, spoken"
        " FROM commands WHERE active=1 ORDER BY device, hour_start"):
    what = f"{r['level']}" if r["on_state"] else "off"
    print(f"    {r['device']:14} {r['hour_start']:02d}-{r['hour_end']:02d} "
          f"{r['day_type']:8} {what:>8}  [{r['source']}]  {r['spoken'][:40]}")

print("\n  SUPERSEDED (retained for audit)")
rows = conn.execute(
    "SELECT id, device, level, hour_start, hour_end, superseded_by, spoken"
    " FROM commands WHERE active=0 ORDER BY id").fetchall()
if not rows:
    print("    none")
for r in rows:
    print(f"    id={r['id']:<3} {r['device']:14} {r['hour_start']:02d}-{r['hour_end']:02d} "
          f"{str(r['level']):>8}  -> superseded_by={r['superseded_by']}  {r['spoken'][:34]}")

print("\n  TABLE COUNTS")
for table in ("telemetry", "usage", "commands", "deployments", "models"):
    count = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    print(f"    {table:12} {count}")

print("\n  DEPLOYMENTS")
for r in conn.execute(
        "SELECT model_v, sha256, size_bytes, ack_at FROM deployments"
        " ORDER BY model_v DESC LIMIT 5"):
    acked = "acked" if r["ack_at"] else "NOT ACKED"
    print(f"    v{r['model_v']:<3} {r['size_bytes']:>6} B  {r['sha256'][:16]}  {acked}")

print()
conn.close()
