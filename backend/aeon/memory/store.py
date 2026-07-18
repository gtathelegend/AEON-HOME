"""
aeon/memory/store.py — Persistent memory store (SQLite via aiosqlite).

All edge-AI state that must survive power loss is written here:
  - Sensor feature vectors (ring buffer, last N days)
  - Policy decisions + user feedback (labels for retraining)
  - Knowledge graph nodes and edges
  - Identity / migration snapshots
  - System events and metrics

The SQLite file lives on the local filesystem. On Snapdragon X Elite this is
typically an NVMe drive; the WAL journal mode ensures durability even on
abrupt power loss.
"""

from __future__ import annotations

import json
import structlog
from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
from pathlib import Path
from typing import Any

import aiosqlite

log = structlog.get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS features (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL,
    ts          TEXT    NOT NULL,
    temperature REAL,
    humidity    REAL,
    motion      INTEGER,
    door_open   INTEGER,
    mean_temp   REAL,
    var_temp    REAL,
    delta_motion REAL
);

CREATE TABLE IF NOT EXISTS decisions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT    NOT NULL,
    frame_seq  INTEGER,
    action     TEXT,
    confidence REAL,
    reason     TEXT,
    label      INTEGER   -- 1=correct, 0=false_alarm, NULL=unlabelled
);

CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    attrs   TEXT NOT NULL   -- JSON
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    src     TEXT NOT NULL,
    dst     TEXT NOT NULL,
    rel     TEXT NOT NULL,
    attrs   TEXT NOT NULL   -- JSON
);

CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    category TEXT,
    name     TEXT,
    payload  TEXT    -- JSON
);

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
"""


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        log.info("memory.store_ready", path=str(self._db_path))

    async def log_feature(self, frame: Any) -> None:
        await self._db.execute(
            "INSERT INTO features (seq,ts,temperature,humidity,motion,"
            "door_open,mean_temp,var_temp,delta_motion) VALUES (?,?,?,?,?,?,?,?,?)",
            (frame.seq, _now_iso(),
             frame.temperature, frame.humidity,
             int(frame.motion), int(frame.door_open),
             frame.mean_temp, frame.var_temp, frame.delta_motion),
        )
        await self._db.commit()

    async def log_decision(self, decision: Any) -> None:
        await self._db.execute(
            "INSERT INTO decisions (ts,frame_seq,action,confidence,reason) VALUES (?,?,?,?,?)",
            (datetime.now(tz=timezone.utc).isoformat(), decision.frame_seq,
             decision.action, decision.confidence, decision.reason),
        )
        await self._db.commit()

    async def log_event(self, category: str, name: str, payload: dict) -> None:
        await self._db.execute(
            "INSERT INTO events (ts,category,name,payload) VALUES (?,?,?,?)",
            (datetime.now(tz=timezone.utc).isoformat(), category, name, json.dumps(payload)),
        )
        await self._db.commit()

    async def label_decision(self, decision_id: int, label: int) -> None:
        await self._db.execute(
            "UPDATE decisions SET label=? WHERE id=?", (label, decision_id)
        )
        await self._db.commit()

    async def get_labelled_samples(
        self, since: datetime, limit: int = 1000
    ) -> list[dict]:
        async with self._db.execute(
            "SELECT f.temperature,f.humidity,f.motion,f.door_open,"
            "f.mean_temp,f.var_temp,f.delta_motion,d.label "
            "FROM decisions d JOIN features f ON d.frame_seq=f.seq "
            "WHERE d.label IS NOT NULL AND d.ts>? LIMIT ?",
            (since.isoformat(), limit),
        ) as cur:
            rows = await cur.fetchall()
        return [
            {"features": list(r[:7]), "label": r[7]}
            for r in rows
        ]

    async def get_recent_events(self, limit: int = 50) -> list[dict]:
        async with self._db.execute(
            "SELECT id, ts, category, name, payload FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
        return [
            {"id": r[0], "ts": r[1], "category": r[2], "name": r[3], "payload": json.loads(r[4] or "{}")}
            for r in rows
        ]

    async def get_sensor_history(self, minutes: int = 60) -> list[dict]:
        async with self._db.execute(
            "SELECT ts, temperature, humidity, motion, mean_temp, delta_motion FROM features "
            "WHERE ts > datetime('now', '-{} minute') ORDER BY id ASC".format(minutes)
        ) as cur:
            rows = await cur.fetchall()
        return [
            {"ts": r[0], "temperature": r[1], "humidity": r[2], "motion": bool(r[3]), "mean_temp": r[4], "delta_motion": r[5]}
            for r in rows
        ]

    async def get_system_stats(self) -> dict:
        stats = {}
        # Size
        try:
            stats["db_size_bytes"] = self._db_path.stat().st_size
        except OSError:
            stats["db_size_bytes"] = 0
            
        # Counts
        for table in ["features", "decisions", "events", "graph_nodes", "graph_edges"]:
            async with self._db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
                row = await cur.fetchone()
                stats[f"{table}_count"] = row[0] if row else 0
        return stats

    # ── Graph persistence ─────────────────────────────────────────────────────

    async def save_node(self, node_id: str, attrs: dict) -> None:
        await self._db.execute(
            "INSERT OR REPLACE INTO graph_nodes (node_id,attrs) VALUES (?,?)",
            (node_id, json.dumps(attrs)),
        )
        await self._db.commit()

    async def save_edge(self, src: str, dst: str, rel: str, attrs: dict) -> None:
        await self._db.execute(
            "INSERT INTO graph_edges (src,dst,rel,attrs) VALUES (?,?,?,?)",
            (src, dst, rel, json.dumps(attrs)),
        )
        await self._db.commit()

    async def load_graph(self) -> tuple[list, list]:
        async with self._db.execute(
            "SELECT node_id, attrs FROM graph_nodes"
        ) as cur:
            node_rows = await cur.fetchall()
        async with self._db.execute(
            "SELECT src, dst, attrs FROM graph_edges"
        ) as cur:
            edge_rows = await cur.fetchall()
        nodes = [(r[0], json.loads(r[1])) for r in node_rows]
        edges = [(r[0], r[1], json.loads(r[2])) for r in edge_rows]
        return nodes, edges

    async def close(self) -> None:
        if self._db:
            await self._db.close()
