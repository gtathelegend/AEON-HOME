"""Durable checkpoints on the node's eMMC.

Framed as  magic | version | length | JSON | CRC32.  JSON inside a framed
envelope means adding a field later does not break older checkpoints.

Writes use the durable-replace pattern -- write to .tmp, fsync, atomic rename,
fsync the directory -- because a write() that returns is not yet on disk; Linux
buffers it in the page cache. That keeps the state file consistent if the device
restarts mid-write.
"""

from __future__ import annotations

import json
import os
import struct
import time
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

MAGIC = b"AEON"
FORMAT_VERSION = 1
GENERATIONS = 3          # how many previous checkpoints to retain

_HEADER = struct.Struct("<4sHI")     # magic, version, payload length


@dataclass
class Checkpoint:
    seq: int = 0                       # monotonic; higher wins
    model_v: int = 0
    model_sha256: str = ""             # which deployed model is live
    schedule: dict = field(default_factory=dict)        # compiled fallback windows
    device_states: dict = field(default_factory=dict)   # what is on, and at what level
    # device_id -> the model's 24-step lag window (~1.1 KB each). Without it a
    # restart leaves the model blind to recent history until a full day rebuilds.
    seq_buffer: dict = field(default_factory=dict)
    ambient_mean: float = 28.0         # normalisation constants, so the node builds
    ambient_std: float = 8.0           # features exactly as the PC did in training
    samples_seen: int = 0
    manual_overrides: int = 0
    spool_offset: int = 0
    wall_clock: float = 0.0


class CorruptCheckpoint(Exception):
    pass


def _encode(ckpt: Checkpoint) -> bytes:
    payload = json.dumps(asdict(ckpt), separators=(",", ":")).encode()
    head = _HEADER.pack(MAGIC, FORMAT_VERSION, len(payload))
    return head + payload + struct.pack("<I", zlib.crc32(payload) & 0xFFFFFFFF)


def _decode(blob: bytes) -> Checkpoint:
    if len(blob) < _HEADER.size + 4:
        raise CorruptCheckpoint("truncated")
    magic, version, length = _HEADER.unpack(blob[:_HEADER.size])
    if magic != MAGIC:
        raise CorruptCheckpoint(f"bad magic {magic!r}")
    if version > FORMAT_VERSION:
        raise CorruptCheckpoint(f"format version {version} is newer than {FORMAT_VERSION}")

    start = _HEADER.size
    payload = blob[start:start + length]
    if len(payload) != length:
        raise CorruptCheckpoint("payload shorter than its declared length")

    (want_crc,) = struct.unpack("<I", blob[start + length:start + length + 4])
    if (zlib.crc32(payload) & 0xFFFFFFFF) != want_crc:
        raise CorruptCheckpoint("crc mismatch")

    data = json.loads(payload)
    # Unknown keys are dropped rather than raising: an older node must still be
    # able to read a checkpoint written by a newer one.
    known = {f for f in Checkpoint.__dataclass_fields__}
    fields = {k: v for k, v in data.items() if k in known}

    # seq_buffer was a flat list before the model landed. A checkpoint written
    # by that build would hand a list to code expecting a per-device dict, so
    # drop it and let the node rebuild rather than crash on restore.
    if not isinstance(fields.get("seq_buffer"), dict):
        fields["seq_buffer"] = {}

    return Checkpoint(**fields)


def save(path: str | Path, ckpt: Checkpoint) -> float:
    """Durable-replace. Returns elapsed milliseconds."""
    t0 = time.perf_counter()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ckpt.wall_clock = time.time()
    blob = _encode(ckpt)

    _rotate(path)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(blob)
        fh.flush()
        os.fsync(fh.fileno())

    os.replace(tmp, path)          # atomic on both POSIX and Windows

    # fsync the directory so the rename itself is durable, not just the bytes.
    # Windows has no directory handle to sync; skip rather than fail.
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except (OSError, AttributeError):
        pass

    return (time.perf_counter() - t0) * 1000


def _rotate(path: Path) -> None:
    """Keep the last GENERATIONS checkpoints as .1, .2, ..."""
    if not path.exists():
        return
    for i in range(GENERATIONS - 1, 0, -1):
        src = path.with_suffix(path.suffix + f".{i}")
        dst = path.with_suffix(path.suffix + f".{i + 1}")
        if src.exists():
            os.replace(src, dst)
    os.replace(path, path.with_suffix(path.suffix + ".1"))


def load(path: str | Path) -> tuple[Checkpoint | None, float, str]:
    """Restore. Returns (checkpoint, elapsed_ms, provenance).

    Tries the live file, then previous generations by age. All fail -> (None, ...)
    and the caller falls back to safe defaults: everything off, ask before acting.
    """
    t0 = time.perf_counter()
    path = Path(path)
    candidates = [path] + [
        path.with_suffix(path.suffix + f".{i}") for i in range(1, GENERATIONS + 1)
    ]

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            ckpt = _decode(candidate.read_bytes())
        except (CorruptCheckpoint, json.JSONDecodeError, TypeError, ValueError):
            continue
        elapsed = (time.perf_counter() - t0) * 1000
        return ckpt, elapsed, candidate.name

    return None, (time.perf_counter() - t0) * 1000, "none"
