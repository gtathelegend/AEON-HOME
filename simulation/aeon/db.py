"""SQLite storage. Local only, on the AI PC.

Single source of truth for preferences. The `commands` table keeps superseded
rows rather than deleting them, so "what did I tell it, and when did it change?"
is answerable.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    node       TEXT    NOT NULL,
    temp_c     REAL,
    rh_pct     REAL,
    motion     INTEGER,
    ts         REAL    NOT NULL,
    created_at REAL    NOT NULL,
    sig_ok     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS usage (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    device   TEXT    NOT NULL,
    on_state INTEGER NOT NULL,
    level    REAL,
    occupied INTEGER,
    source   TEXT    NOT NULL CHECK (source IN ('auto', 'manual', 'phone')),
    ts       REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS commands (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device        TEXT    NOT NULL,
    on_state      INTEGER NOT NULL,
    level         REAL,
    hour_start    INTEGER NOT NULL,
    hour_end      INTEGER NOT NULL,
    day_type      TEXT    NOT NULL CHECK (day_type IN ('all', 'weekday', 'weekend')),
    spoken        TEXT,
    stated_at     REAL    NOT NULL,
    source        TEXT    NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    superseded_by INTEGER REFERENCES commands(id)
);

CREATE TABLE IF NOT EXISTS deployments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model_v     INTEGER NOT NULL,
    sha256      TEXT    NOT NULL,
    size_bytes  INTEGER NOT NULL,
    deployed_at REAL    NOT NULL,
    ack_at      REAL
);

CREATE TABLE IF NOT EXISTS models (
    model_v      INTEGER PRIMARY KEY,
    cv_auc       REAL,
    level_mae    TEXT,
    n_windows    INTEGER,
    params       INTEGER,
    train_secs   REAL,
    trained_at   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cmd_active ON commands(device, active);
CREATE INDEX IF NOT EXISTS idx_usage_ts   ON usage(ts);
CREATE INDEX IF NOT EXISTS idx_tel_ts     ON telemetry(ts);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # WAL survives a crash mid-write and lets a reader run during a write.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- telemetry ---------------------------------------------------------

    def record_telemetry(self, node: str, temp_c: float, rh_pct: float,
                         motion: int, ts: float, sig_ok: bool) -> None:
        self.conn.execute(
            "INSERT INTO telemetry (node, temp_c, rh_pct, motion, ts, created_at, sig_ok)"
            " VALUES (?,?,?,?,?,?,?)",
            (node, temp_c, rh_pct, motion, ts, time.time(), int(sig_ok)),
        )
        self.conn.commit()

    def telemetry_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) c FROM telemetry").fetchone()["c"]

    # -- usage -------------------------------------------------------------

    def record_usage(self, device: str, on: bool, level: float | None,
                     occupied: bool, source: str, ts: float) -> None:
        self.conn.execute(
            "INSERT INTO usage (device, on_state, level, occupied, source, ts)"
            " VALUES (?,?,?,?,?,?)",
            (device, int(on), level, int(occupied), source, ts),
        )
        self.conn.commit()

    def usage_rows(self, device: str | None = None) -> list[sqlite3.Row]:
        if device:
            return self.conn.execute(
                "SELECT * FROM usage WHERE device=? ORDER BY ts", (device,)).fetchall()
        return self.conn.execute("SELECT * FROM usage ORDER BY ts").fetchall()

    # -- commands ----------------------------------------------------------

    def insert_command(self, device: str, on: bool, level: float | None,
                       hour_start: int, hour_end: int, day_type: str,
                       spoken: str, source: str, stated_at: float) -> int:
        cur = self.conn.execute(
            "INSERT INTO commands"
            " (device, on_state, level, hour_start, hour_end, day_type, spoken,"
            "  stated_at, source, active)"
            " VALUES (?,?,?,?,?,?,?,?,?,1)",
            (device, int(on), level, hour_start, hour_end, day_type, spoken,
             stated_at, source),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def mark_superseded(self, old_ids: list[int], new_id: int) -> None:
        if not old_ids:
            return
        self.conn.executemany(
            "UPDATE commands SET active=0, superseded_by=? WHERE id=?",
            [(new_id, i) for i in old_ids],
        )
        self.conn.commit()

    def active_commands(self, device: str | None = None) -> list[sqlite3.Row]:
        if device:
            return self.conn.execute(
                "SELECT * FROM commands WHERE active=1 AND device=? ORDER BY hour_start",
                (device,)).fetchall()
        return self.conn.execute(
            "SELECT * FROM commands WHERE active=1 ORDER BY device, hour_start").fetchall()

    def all_commands(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM commands ORDER BY stated_at").fetchall()

    def last_active_command(self) -> sqlite3.Row | None:
        """Target of a follow-up like "change it to 23"."""
        return self.conn.execute(
            "SELECT * FROM commands WHERE active=1 ORDER BY stated_at DESC LIMIT 1"
        ).fetchone()

    # -- models & deployments ---------------------------------------------

    def record_model(self, model_v: int, cv_auc: float | None, level_mae: str,
                     n_windows: int, params: int, train_secs: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO models"
            " (model_v, cv_auc, level_mae, n_windows, params, train_secs, trained_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (model_v, cv_auc, level_mae, n_windows, params, train_secs, time.time()),
        )
        self.conn.commit()

    def record_deployment(self, model_v: int, sha256: str, size_bytes: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO deployments (model_v, sha256, size_bytes, deployed_at)"
            " VALUES (?,?,?,?)",
            (model_v, sha256, size_bytes, time.time()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def ack_deployment(self, deployment_id: int) -> None:
        self.conn.execute("UPDATE deployments SET ack_at=? WHERE id=?",
                          (time.time(), deployment_id))
        self.conn.commit()

    def latest_model_v(self) -> int:
        row = self.conn.execute("SELECT MAX(model_v) v FROM models").fetchone()
        return int(row["v"]) if row and row["v"] is not None else 0

    def deployment_for(self, model_v: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM deployments WHERE model_v=? ORDER BY id DESC LIMIT 1",
            (model_v,)).fetchone()

    def model_for(self, model_v: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM models WHERE model_v=?", (model_v,)).fetchone()

    def latest_model(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM models ORDER BY model_v DESC LIMIT 1").fetchone()
