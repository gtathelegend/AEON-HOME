#!/usr/bin/env python3
"""Why can the phone not reach the hub?

    python tools/netcheck.py

Answers, in order, the questions that actually distinguish the causes:

  1. Is the hub listening, and on all interfaces or just loopback?
  2. Is discovery bound to UDP 8801?
  3. Does the firewall permit THIS python executable inbound?
  4. What address should the phone use, and is the network Public?

Then prints the two checks only the phone can perform. Most "it will not
connect" reports are a network isolating its clients, which no amount of code
fixes -- and this tells you that in thirty seconds rather than at the venue.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PORT = 8800
DISCOVERY_PORT = 8801


def line(status: str, text: str) -> None:
    print(f"  {status:5} {text}")


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> int:
    print("\n  AEON - can the phone reach this machine?")
    print("  " + "=" * 56)

    ip = lan_ip()
    problems = []

    print("\n  HUB")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=4) as r:
            line("OK", f"hub answers on loopback (HTTP {r.status})")
    except Exception:
        line("BAD", f"nothing on 127.0.0.1:{PORT} - is the hub running?")
        problems.append("hub not running")

    if ip.startswith("127."):
        line("BAD", "no LAN address - this machine is not on a network")
        problems.append("no LAN address")
    else:
        try:
            with urllib.request.urlopen(f"http://{ip}:{PORT}/", timeout=4) as r:
                line("OK", f"hub answers on {ip} (HTTP {r.status}) - bound to all interfaces")
        except Exception:
            line("BAD", f"hub does NOT answer on {ip} - bound to loopback only?")
            problems.append("not listening on the LAN address")

    print("\n  DISCOVERY")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(2.0)
    try:
        s.sendto(b"AEON?", ("255.255.255.255", DISCOVERY_PORT))
        data, addr = s.recvfrom(512)
        reply = json.loads(data.decode())
        line("OK", f"hub answered discovery: host={reply.get('host')} port={reply.get('port')}")
        if reply.get("host") != ip:
            line("note", f"discovery reports {reply.get('host')} but LAN address is {ip}")
    except Exception:
        line("BAD", f"no answer on UDP {DISCOVERY_PORT} - discovery is not running")
        problems.append("discovery not answering")
    finally:
        s.close()

    print("\n  FIREWALL")
    # Both paths matter. A venv's Scripts\python.exe runs with the BASE
    # interpreter as its process image on Windows, and the firewall matches on
    # the image -- so a rule naming either one can be the one doing the work.
    candidates = {sys.executable}
    base = getattr(sys, "_base_executable", None)
    if base:
        candidates.add(base)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetFirewallRule -ErrorAction SilentlyContinue | "
             "Where-Object { $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' -and $_.Enabled -eq 'True' } | "
             "ForEach-Object { ($_ | Get-NetFirewallApplicationFilter).Program }"],
            capture_output=True, text=True, timeout=45,
        )
        programs = {p.strip().lower() for p in out.stdout.splitlines() if p.strip()}
        covered = sorted(c for c in candidates if c.lower() in programs)
        if covered:
            line("OK", "an inbound Allow rule covers the interpreter serving this hub")
            for c in covered:
                line("", f"  {c}")
        else:
            line("note", "no inbound Allow rule names either of:")
            for c in sorted(candidates):
                line("", f"  {c}")
            line("", "  Windows prompts on first EXTERNAL connection - allow it.")
        line("note", "this cannot be settled from this machine: a request from")
        line("note", "here never crosses the firewall. Only the phone can prove it.")
    except Exception as exc:
        line("note", f"could not read firewall rules ({type(exc).__name__})")

    print("\n  NETWORK")
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetConnectionProfile | ForEach-Object { \"$($_.Name)|$($_.NetworkCategory)\" }"],
            capture_output=True, text=True, timeout=30,
        )
        for entry in out.stdout.splitlines():
            if "|" in entry:
                name, category = entry.split("|", 1)
                line("", f"{name.strip()} - {category.strip()}")
                if category.strip().lower() == "public":
                    line("note", "Public profile. Venue and office WiFi often isolate")
                    line("note", "clients, which blocks phone->laptop entirely.")
    except Exception:
        pass

    print("\n  " + "=" * 56)
    print("  WHAT THE PHONE MUST SEE")
    print(f"    1. open  http://{ip}:{PORT}/phone  in the phone's browser")
    print("       loads  -> the network is fine; the problem is in the app")
    print("       fails  -> the network is blocking it; no app change helps")
    print("    2. watch this hub's console while you press the mic:")
    print("       '[discovery] probe from ...'  = the phone reached the laptop")
    print("       '[ws] phone connected from ...' = the socket opened")
    print("       nothing at all                = packets never arrived")
    print()
    if problems:
        print(f"  {len(problems)} problem(s) on this machine:")
        for p in problems:
            print(f"    - {p}")
    else:
        print("  This machine is serving correctly. If the phone still cannot")
        print("  connect, the network between them is the cause -- use a phone")
        print("  hotspot with the laptop joined to it.")
    print()
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
