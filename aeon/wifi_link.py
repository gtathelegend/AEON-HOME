"""Store-and-forward transport, node -> PC.

TCP, newline-delimited signed JSON. Tokens spool to eMMC when the PC is
unreachable and replay on reconnect, so a preference is never lost because a
laptop was asleep.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

BACKOFF = [1, 2, 5, 10, 20]          # seconds
SPOOL_CAP_BYTES = 8 * 1024 * 1024    # 8 MB, then the oldest half is trimmed


class WifiLink:
    def __init__(self, host: str, port: int, spool_path: str | Path) -> None:
        self.host = host
        self.port = port
        self.spool_path = Path(spool_path)
        self.spool_path.parent.mkdir(parents=True, exist_ok=True)

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._fails = 0
        self._next_attempt = 0.0
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    # -- connection --------------------------------------------------------

    async def _ensure(self, force: bool = False) -> bool:
        if self.connected:
            return True
        if not force and time.monotonic() < self._next_attempt:
            return False
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=2.0)
            self._fails = 0
            self._next_attempt = 0.0
            return True
        except (OSError, asyncio.TimeoutError):
            self._drop()
            delay = BACKOFF[min(self._fails, len(BACKOFF) - 1)]
            self._fails += 1
            self._next_attempt = time.monotonic() + delay
            return False

    def _drop(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass
        self._reader = self._writer = None

    def reset_backoff(self) -> None:
        """Try again immediately -- the user just told us the PC is back."""
        self._fails = 0
        self._next_attempt = 0.0

    async def close(self) -> None:
        self._drop()

    # -- sending -----------------------------------------------------------

    async def _write(self, msg: dict) -> bool:
        try:
            self._writer.write(json.dumps(msg).encode() + b"\n")
            await asyncio.wait_for(self._writer.drain(), timeout=2.0)
            return True
        except (OSError, asyncio.TimeoutError, AttributeError):
            self._drop()
            return False

    async def send(self, msg: dict) -> str:
        """`delivered` or `spooled`. Never raises -- the caller has a house to run."""
        async with self._lock:
            if await self._ensure() and await self._write(msg):
                return "delivered"
            self._spool(msg)
            return "spooled"

    # -- spool -------------------------------------------------------------

    def _spool(self, msg: dict) -> None:
        with open(self.spool_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(msg) + "\n")
        self._trim()

    def _trim(self) -> None:
        if not self.spool_path.exists():
            return
        if self.spool_path.stat().st_size <= SPOOL_CAP_BYTES:
            return
        lines = self.spool_path.read_text(encoding="utf-8").splitlines()
        keep = lines[len(lines) // 2:]     # drop the oldest half
        self.spool_path.write_text("\n".join(keep) + "\n", encoding="utf-8")

    def spool_count(self) -> int:
        if not self.spool_path.exists():
            return 0
        return sum(1 for line in self.spool_path.read_text(encoding="utf-8").splitlines()
                   if line.strip())

    async def flush(self, force: bool = True) -> int:
        """Replay spooled tokens. Returns how many were delivered."""
        async with self._lock:
            if self.spool_count() == 0:
                return 0
            if force:
                self.reset_backoff()
            if not await self._ensure(force=force):
                return 0

            lines = [l for l in self.spool_path.read_text(encoding="utf-8").splitlines()
                     if l.strip()]
            delivered = 0
            for i, line in enumerate(lines):
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    delivered += 1          # unparseable: drop it, don't wedge the spool
                    continue
                if not await self._write(msg):
                    # Keep everything we did not manage to send.
                    remaining = lines[i:]
                    self.spool_path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
                    return delivered
                delivered += 1

            self.spool_path.write_text("", encoding="utf-8")
            return delivered
