"""Answer "where is the hub?" on the local network.

The phone should never ask a person for an IP address. Baking one into the APK
does not survive contact with reality either -- this laptop's address moved from
172.20.10.8 to 10.92.213.203 in one night simply by changing WiFi, and a venue
will move it again. So the hub answers for itself.

A one-packet UDP protocol, deliberately:

    phone  ── broadcast "AEON?" ──▶ 255.255.255.255:8801
    hub    ── {"aeon":1,"host":...,"port":8800,...} ──▶ phone

No mDNS: Android's NSD stack is inconsistent across vendors and adds a
dependency for what is one datagram. No subnet sweep: 254 probes to find one
laptop is slow and looks like a port scan to anything watching.

If the network blocks broadcast, discovery finds nothing -- and that same
network would have blocked the WebSocket anyway, so failing here is an early,
honest signal rather than a new failure mode.
"""

from __future__ import annotations

import asyncio
import json
import socket

DISCOVERY_PORT = 8801
PROBE = b"AEON?"
MAX_DATAGRAM = 512


class _Responder(asyncio.DatagramProtocol):
    def __init__(self, hub_port: int) -> None:
        self.hub_port = hub_port
        self.transport: asyncio.DatagramTransport | None = None
        self.answered = 0

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if not data.startswith(PROBE):
            # Logged too: a stray packet arriving proves the network delivers
            # broadcast to this host, which is exactly what you want to know
            # when the phone claims it cannot find the hub.
            print(f"  [discovery] ignored {len(data)} B from {addr[0]} "
                  f"(not an AEON probe)", flush=True)
            return
        # Report the address THIS host reaches the asker on, rather than a
        # guess: a laptop on WiFi and Ethernet at once has more than one, and
        # only one of them is the one the phone can use.
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect((addr[0], self.hub_port))
            host = probe.getsockname()[0]
            probe.close()
        except OSError:
            host = ""

        reply = json.dumps({
            "aeon": 1,
            "host": host,
            "port": self.hub_port,
            "ws": f"ws://{host}:{self.hub_port}/ws",
        }).encode()

        if self.transport is not None and len(reply) <= MAX_DATAGRAM:
            self.transport.sendto(reply, addr)
            self.answered += 1
            print(f"  [discovery] probe from {addr[0]}:{addr[1]} -> answered "
                  f"host={host or '?'} port={self.hub_port}", flush=True)
        else:
            print(f"  [discovery] probe from {addr[0]} -> COULD NOT ANSWER "
                  f"(transport={self.transport is not None}, {len(reply)} B)",
                  flush=True)

    def error_received(self, exc: Exception) -> None:
        pass                            # a bad datagram must not kill the socket


async def serve(hub_port: int = 8800, port: int = DISCOVERY_PORT):
    """Start answering discovery probes. Returns (transport, protocol).

    Never fatal: if the port is taken -- a second hub, or something else on
    8801 -- the hub still runs and the app falls back to its baked-in address.
    """
    loop = asyncio.get_running_loop()
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: _Responder(hub_port),
            local_addr=("0.0.0.0", port),
            allow_broadcast=True,
        )
        print(f"  [discovery] listening on UDP 0.0.0.0:{port} "
              f"(phones broadcast 'AEON?' here)", flush=True)
        return transport, protocol
    except OSError as exc:
        # Not fatal, but say so loudly: silent discovery looks identical to a
        # network that drops broadcast, and they need very different fixes.
        print(f"  [discovery] DISABLED - could not bind UDP {port}: {exc}",
              flush=True)
        return None, None
