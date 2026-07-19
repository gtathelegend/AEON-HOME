"""The AI PC. Learns, and can be switched off.

Holds the SQLite store -- the single source of truth for preferences -- and
listens on TCP for the central node. It is required to learn and never required
to run: close the laptop and the house keeps working.

Phase 2 "trains" by compiling the active commands into a fallback schedule.
Phase 3 replaces that with a real sequence model exported to ONNX; the deploy
mechanics here (manifest, sha256, device_order check, ack) do not change.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time

from . import aihub, commands, devices, protocol, sequence, tsmodel
from .db import Database

# The node talks about who drove a change (phone, model, boot); the usage table
# records how it was driven (auto, manual, phone). Translate at the boundary
# rather than widening the CHECK constraint until it stops constraining anything.
USAGE_SOURCE = {
    "phone": "phone",
    "manual": "manual",
    "model": "auto",
    "schedule": "auto",
    "boot": "auto",
}


class PCHub:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.host = "127.0.0.1"
        self.port = 0
        self._server: asyncio.AbstractServer | None = None
        self._writers: set[asyncio.StreamWriter] = set()

        self.received = 0
        self.rejected = 0
        self.last_error: str | None = None
        self.last_result = None      # most recent TrainResult, for AI Hub

    # -- lifecycle ---------------------------------------------------------

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        # Idempotent: starting an already-listening PC would otherwise raise
        # "only one usage of each socket address", which reads as a port
        # conflict rather than as double-start.
        if self._server is not None:
            return self.port
        self.host = host
        self._server = await asyncio.start_server(self._handle, host, port or self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self, grace: float = 0.15) -> None:
        """Close the laptop. The socket really goes away.

        Two requirements pull against each other here:

        * A node still holding the link must not go on talking to a PC that is
          switched off, so the live sockets have to close -- not just the
          listener. Same lesson as LeafDevice.stop().
        * A preference the node was already told was `delivered` must not
          vanish because the laptop shut a moment later. `WifiLink.send()`
          reports delivered once the bytes drain, which says nothing about this
          side having read them, so they can still be sitting unread in a
          handler's buffer when this is called.

        So: stop accepting, let the handlers drain what they already hold, then
        force the rest shut. The drain is a bounded wait rather than
        `wait_closed()`, which since Python 3.12.1 waits for every handler to
        return -- and `_handle` only returns when its peer hangs up, so on its
        own it would block here forever.

        A leaf models pulling the plug and is right to drop everything mid-flight.
        A PC that drops an acknowledged preference has lost the one thing it
        exists to keep, so this shutdown is orderly. Pass grace=0 for a hard cut.
        """
        if self._server is None:
            return

        self._server.close()

        if grace > 0 and self._writers:
            await asyncio.sleep(grace)

        for writer in list(self._writers):
            try:
                writer.close()
            except Exception:
                pass
        self._writers.clear()

        try:
            await self._server.wait_closed()
        except Exception:
            pass
        self._server = None

    @property
    def reachable(self) -> bool:
        return self._server is not None

    # -- inbound from the node --------------------------------------------

    async def _handle(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        self._writers.add(writer)
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                try:
                    response = self.ingest(msg)
                except Exception as exc:
                    # One unstorable row must not sever the link. An earlier
                    # build let a CHECK-constraint failure propagate out of this
                    # handler: the socket died, every later preference spooled,
                    # and the dashboard showed a healthy node talking to nobody.
                    self.last_error = f"{type(exc).__name__}: {exc}"
                    self.rejected += 1
                    response = protocol.reject(f"ingest failed: {exc}")
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self._writers.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    def ingest(self, msg: dict) -> dict:
        if not protocol.verify(msg):
            self.rejected += 1
            return protocol.reject("bad signature")

        typ = msg.get("typ")
        self.received += 1

        if typ == "preference":
            cmd_id, superseded = self.store_preference(msg)
            return {"status": "ok", "command_id": cmd_id, "superseded": superseded}

        if typ == "telemetry":
            self.db.record_telemetry(
                node=msg.get("iss", "node:unknown"),
                temp_c=msg.get("temp_c"), rh_pct=msg.get("rh_pct"),
                motion=msg.get("motion", 0), ts=msg.get("ts", time.time()),
                sig_ok=True,
            )
            return {"status": "ok"}

        if typ == "usage":
            self.db.record_usage(
                device=msg["device"], on=bool(msg["on"]), level=msg.get("level"),
                occupied=bool(msg.get("occupied")),
                source=USAGE_SOURCE.get(msg.get("src", ""), "auto"),
                ts=msg.get("ts", time.time()),
            )
            return {"status": "ok"}

        return protocol.reject(f"unsupported type {typ!r}")

    # -- preferences -------------------------------------------------------

    def store_preference(self, msg: dict) -> tuple[int, list[int]]:
        """Store, superseding any active command covering the same window.

        Supersession, not append. Say "25 at 9 PM" then "23 at 9 PM"; store both
        and the model learns 24 -- the average of two things, one of which the
        user explicitly retracted. Full history is retained for audit; only the
        active set is ever trained on.
        """
        intent = commands.Intent(
            device=msg["device"], on=bool(msg["on"]), level=msg.get("level"),
            hour_start=int(msg.get("hour_start", 0)),
            hour_end=int(msg.get("hour_end", 24)),
            day_type=msg.get("day_type", commands.DAY_ALL),
            spoken=msg.get("spoken", ""),
        )

        overlapping = [
            row["id"] for row in self.db.active_commands(intent.device)
            if commands.overlaps(row, intent)
        ]

        cmd_id = self.db.insert_command(
            device=intent.device, on=intent.on, level=intent.level,
            hour_start=intent.hour_start, hour_end=intent.hour_end,
            day_type=intent.day_type, spoken=intent.spoken,
            source=msg.get("src", "phone"), stated_at=msg.get("ts", time.time()),
        )
        self.db.mark_superseded(overlapping, cmd_id)
        return cmd_id, overlapping

    def seed_defaults(self) -> int:
        """Seed starting behaviour, once, on an empty database.

        These are ordinary rows with source='default' -- visible in the commands
        table and superseded by anything you say. They exist so a fresh install
        does something on its first evening instead of sitting dark.
        """
        if self.db.active_commands():
            return 0

        seeds = [
            ("light.living", True, 6500.0, 7, 18, "daylight during the day"),
            ("light.living", True, 3000.0, 18, 23, "warm light in the evening"),
            ("light.living", True, 2200.0, 23, 24, "night light after 11"),
            ("fan.bedroom",  True, 70.0,   13, 17, "fan through the afternoon"),
            ("ac.living",    True, 25.0,   21, 23, "AC at night"),
            ("vacuum.home",  True, 70.0,   10, 12, "vacuum through the late morning"),
        ]
        for device, on, level, h0, h1, spoken in seeds:
            self.db.insert_command(
                device=device, on=on, level=level, hour_start=h0, hour_end=h1,
                day_type=commands.DAY_ALL, spoken=spoken, source="default",
                stated_at=time.time(),
            )
        return len(seeds)

    # -- "training" --------------------------------------------------------

    def compile_policy(self) -> tuple[bytes, str, dict]:
        """Active preferences -> (blob, sha256, stats). No side effects.

        Separate from retrain() so a caller can ask "would this change
        anything?" without minting a model version. Deploying an identical
        policy churns the version number and makes the deployment log useless
        for answering "when did behaviour actually change?".
        """
        t0 = time.perf_counter()
        active = self.db.active_commands()
        schedule = commands.compile_schedule(active)

        # sort_keys matters: an unstable serialisation gives a different hash for
        # identical content, which defeats the comparison above.
        blob = json.dumps(schedule, sort_keys=True, separators=(",", ":")).encode()
        sha = hashlib.sha256(blob).hexdigest()

        covered = sum(len(hours) for dev in schedule.values() for hours in dev.values())
        stats = {
            "n_windows": covered,
            "params": 0,
            "cv_auc": None,
            "level_mae": {},
            "train_secs": time.perf_counter() - t0,
            "active_commands": len(active),
        }
        return blob, sha, stats

    def retrain(self, use_aihub: bool = False, aihub_device: str | None = None,
                incumbent_onnx: bytes | None = None) -> tuple[dict, bytes, dict]:
        """Train a sequence model, export it, quantise it, hash it.

        Returns (manifest, blob, stats). The blob is the int8 ONNX; the manifest
        carries everything the node needs to build features exactly the way the
        PC did -- level ranges, device order, ambient normalisation constants,
        the warm-start window, and the compiled schedule as a fallback.

        A rejected candidate never leaves this machine.
        """
        active = self.db.active_commands()
        incumbent = self.db.latest_model()
        incumbent_auc = incumbent["cv_auc"] if incumbent else None

        # What the house actually did, alongside what it was told. Pooled, not
        # swapped -- see tsmodel.train(). On a fresh install this is empty and
        # training falls back to the stated rules alone.
        result = tsmodel.train(active, incumbent_auc=incumbent_auc,
                               usage_rows=self.db.usage_rows(),
                               incumbent_onnx=incumbent_onnx)
        # Kept so a caller can hand the fp32 graph to AI Hub without retraining.
        # AI Hub compiles the fp32 export, not the locally quantised int8.
        self.last_result = result

        # The compiled schedule ships regardless: it is the node's fallback for
        # when the model file is missing or its hash fails. Learning is
        # centralised; control is not.
        schedule_blob, schedule_sha, schedule_stats = self.compile_policy()

        if not result.ok:
            stats = dict(schedule_stats)
            # Carry the training figures through the rejection too. "Not better"
            # is a result the screen shows, and showing it with zeroes in every
            # field reads as a crash rather than as a verdict.
            stats.update({"rejected": result.reason, "kind": "schedule",
                          "cv_auc": result.cv_auc, "n_windows": result.n_windows,
                          "stated_windows": result.stated_windows,
                          "observed_windows": result.observed_windows,
                          "observed_hours": result.observed_hours,
                          "incumbent_auc_measured": result.incumbent_auc_measured,
                          "level_mae": result.level_mae,
                          "train_secs": result.train_seconds})
            return {}, b"", stats

        blob = result.onnx_int8
        model_v = self.db.latest_model_v() + 1

        aihub_report = None
        if use_aihub:
            aihub_report = self._optimise_on_aihub(result, aihub_device)

        stats = {
            "kind": "int8 ONNX",
            "n_windows": result.n_windows,
            "params": result.params,
            "cv_auc": result.cv_auc,
            "level_mae": result.level_mae,
            "train_secs": result.train_seconds,
            "iterations": result.iterations,
            "fp32_bytes": len(result.onnx_fp32),
            "active_commands": len(active),
            "stated_windows": result.stated_windows,
            "observed_windows": result.observed_windows,
            "observed_hours": result.observed_hours,
            "incumbent_auc_measured": result.incumbent_auc_measured,
            "aihub": aihub_report,
        }

        self.db.record_model(
            model_v=model_v, cv_auc=result.cv_auc,
            level_mae=json.dumps(result.level_mae),
            n_windows=result.n_windows, params=result.params,
            train_secs=result.train_seconds,
        )

        manifest = protocol.policy_update(
            model_v=model_v, sha256=result.sha256, size_bytes=len(blob),
            device_order=devices.DEVICE_ORDER, level_ranges=devices.level_ranges(),
            ambient_mean=result.ambient_mean, ambient_std=result.ambient_std,
            kind="int8 ONNX",
        )
        # Unsigned extras would break the HMAC, so add them before re-signing.
        manifest = dict(manifest)
        manifest["window"] = sequence.WINDOW
        manifest["input_dim"] = sequence.INPUT_DIM
        manifest["warm_start"] = result.warm_start
        manifest["schedule"] = json.loads(schedule_blob)
        manifest["schedule_sha256"] = schedule_sha
        manifest = protocol.sign(manifest)

        return manifest, blob, stats

    def _optimise_on_aihub(self, result, device_name: str | None) -> dict:
        """Compile and profile on real Snapdragon silicon, if configured.

        Never fatal. The locally quantised int8 artefact is what deploys either
        way; AI Hub adds measured on-device numbers, not a dependency.
        """
        report = aihub.optimize(
            result.onnx_fp32,
            device_name=device_name or aihub.DEFAULT_DEVICE,
        )
        return {
            "ok": report.ok,
            "reason": report.reason,
            "device": report.device,
            "target_runtime": report.target_runtime,
            "compile_job": report.compile_job,
            "profile_job": report.profile_job,
            "inference_us": report.inference_us,
            "peak_memory_mb": report.peak_memory_mb,
            "compute_unit": report.compute_unit,
            "artefact_bytes": len(report.artefact),
            "elapsed_s": round(report.elapsed_s, 1),
        }

    def learned_rows(self) -> list[dict]:
        """The "Learned" panel, built from the active command set."""
        rows = []
        for row in self.db.active_commands():
            d = devices.get(row["device"])
            what = d.format_level(row["level"]) if row["on_state"] else "off"
            when = f"{row['hour_start']:02d}-{row['hour_end']:02d}"
            scope = {"all": "Daily", "weekday": "Mon-Fri", "weekend": "Sat/Sun"}[row["day_type"]]
            rows.append({
                "device": row["device"],
                "label": d.label,
                "text": f"{scope} {when}  {what}",
                "source": row["source"],
            })
        rows.append({"device": "*", "label": devices.occupancy_rule_label(),
                     "text": "Off when the room is empty", "source": "rule"})
        return rows
