"""
aeon/learning/loop.py — Continuous on-device learning loop orchestrator.

Exposes real counters that the WebSocket bus reads for the dashboard:
  - false_alarms_flagged
  - adaptation_progress_pct
  - training_state
  - last_train_ts
"""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.learning.dataset import DatasetGenerator
from core.learning.trainer import IncrementalTrainer
from core.learning.versioning import ModelVersionControl
from core.learning.dream import DreamState

log = structlog.get_logger(__name__)

MIN_SAMPLES_FOR_TRAINING = 20
TRAINING_INTERVAL_HOURS  = 6


class LearningLoop:
    def __init__(self, memory: Any, qnn: Any, model_dir: Path) -> None:
        self._memory    = memory
        self._qnn       = qnn
        self._model_dir = model_dir

        # ── Observable state (read by WebSocket bus) ──────────────────────────
        self.false_alarms_flagged:   int   = 0
        self.adaptation_progress_pct: int  = 0   # 0-100, advances during training
        self.training_state:          str  = "idle"
        self.last_train_ts:           str | None = None

        # ── Private timing ────────────────────────────────────────────────────
        self._last_train: datetime | None = None

        # ── Sub-components ────────────────────────────────────────────────────
        self._dataset    = DatasetGenerator(memory=memory)
        self._trainer    = IncrementalTrainer(
            state_path=model_dir / "presence_classifier.pkl"
        )
        self._versioning = ModelVersionControl(
            model_dir=model_dir,
            model_name="presence_classifier",
            qnn=qnn,
        )
        self._dream = DreamState(memory=memory, graph=getattr(memory, "_graph", None))

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def trainer(self) -> IncrementalTrainer:
        return self._trainer

    @property
    def dream_state(self) -> DreamState:
        return self._dream

    # ── Bus wiring ────────────────────────────────────────────────────────────

    def attach_bus(self, ws_bus: Any) -> None:
        """Inject WebSocket bus so DreamState can broadcast progress."""
        self._dream.attach_bus(ws_bus)

    def attach_graph(self, graph: Any) -> None:
        """Inject knowledge graph into DreamState after main wires everything."""
        self._dream._graph = graph

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        while True:
            await asyncio.sleep(3600)
            await self._maybe_train()
            now = datetime.now()
            if 2 <= now.hour <= 4:
                await self._dream.enter()

    # ── Training ──────────────────────────────────────────────────────────────

    async def _maybe_train(self) -> None:
        if self._last_train is not None:
            elapsed = datetime.now(tz=timezone.utc) - self._last_train
            if elapsed < timedelta(hours=TRAINING_INTERVAL_HOURS):
                return

        self.training_state = "collecting_data"
        self.adaptation_progress_pct = 5

        since = self._last_train or datetime.min
        X, y = await self._dataset.generate(since=since)

        if len(y) < MIN_SAMPLES_FOR_TRAINING:
            log.info("learning.skip", samples=len(y), minimum=MIN_SAMPLES_FOR_TRAINING)
            self.training_state = "idle"
            self.adaptation_progress_pct = 0
            return

        log.info("learning.train_start", samples=len(y))
        self.training_state = "training"
        self.adaptation_progress_pct = 30

        try:
            if len(y) > 10:
                split_idx = int(len(y) * 0.8)
                X_train, X_test = X[:split_idx], X[split_idx:]
                y_train, y_test = y[:split_idx], y[split_idx:]
            else:
                X_train, X_test, y_train, y_test = X, X, y, y

            self.adaptation_progress_pct = 50
            prev_acc = await asyncio.to_thread(self._trainer.evaluate, X_test, y_test)

            self.adaptation_progress_pct = 65
            metrics = await asyncio.to_thread(self._trainer.train_batch, X_train, y_train)

            self.adaptation_progress_pct = 80
            new_acc = await asyncio.to_thread(self._trainer.evaluate, X_test, y_test)

            self.training_state = "evaluating"
            self.adaptation_progress_pct = 90
            deployed = self._versioning.evaluate_and_deploy(
                new_accuracy=new_acc, previous_accuracy=prev_acc
            )

            if deployed:
                await self._qnn.reload_model("presence_classifier")
                self.training_state = "deployed"
            else:
                self.training_state = "rolled_back"

            self._last_train = datetime.now(tz=timezone.utc)
            self.last_train_ts = self._last_train.isoformat()
            self.adaptation_progress_pct = 100
            log.info("learning.train_complete", deployed=deployed, metrics=metrics)

        except Exception:
            log.exception("learning.train_error")
            self.training_state = "error"
            self.adaptation_progress_pct = 0
        finally:
            # Reset progress after a short delay so dashboard shows final state
            await asyncio.sleep(5)
            if self.training_state not in ("error",):
                self.training_state = "idle"
            self.adaptation_progress_pct = 0

    # ── Public triggers ───────────────────────────────────────────────────────

    async def trigger_online_learning(self) -> None:
        log.info("learning.online_triggered")
        await self._maybe_train()

    async def trigger_dream_state(self) -> None:
        log.info("learning.dream_triggered")
        await self._dream.enter()

    def record_false_alarm(self) -> None:
        """Increment the false alarm counter (called by WS bus or API)."""
        self.false_alarms_flagged += 1
        self._trainer.update_threshold(-0.05)
