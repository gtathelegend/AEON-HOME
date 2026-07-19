#!/usr/bin/env python3
"""Start the ÆON Home hub.

    python run.py                    # Phase 2: the real system
    python run.py --phase 1          # Phase 1: scripted house, no sockets, no DB
    python run.py --port 8800 --reset

Open the dashboard on the AI PC, and the phone URL on your phone. Both must be
on the same WiFi; nothing else is required.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import uvicorn

# The Windows console defaults to cp1252, which cannot encode "ÆON" or box-drawing
# rules -- the banner then kills the process before the server ever starts.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from aeon.server import create_app, lan_ip


def main() -> None:
    ap = argparse.ArgumentParser(description="AEON Home hub")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--phase", type=int, default=2, choices=(1, 2),
                    help="1 = scripted house, 2 = real sockets + SQLite")
    ap.add_argument("--data", default="data", help="where the DB, checkpoint and spool live")
    ap.add_argument("--reset", action="store_true",
                    help="wipe the data directory first - a clean demo every time")
    args = ap.parse_args()

    if args.reset and Path(args.data).exists():
        shutil.rmtree(args.data)

    if args.phase == 1:
        from aeon.demo_source import ScriptedHouse
        source = ScriptedHouse()
        backing = "scripted house (no sockets, no database)"
    else:
        from aeon.live_source import LiveHouse
        source = LiveHouse(args.data)
        backing = f"SQLite + TCP leaves + eMMC checkpoints in ./{args.data}/"

    app = create_app(source, port=args.port)
    ip = lan_ip()

    print()
    print("  ÆON HOME · HUB")
    print("  " + "─" * 52)
    print(f"  dashboard   http://localhost:{args.port}/")
    print(f"  phone       http://{ip}:{args.port}/phone")
    print("  " + "─" * 52)
    print(f"  phase {args.phase} · {backing}")
    print("  same WiFi, no cloud, no pairing")
    print()

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
