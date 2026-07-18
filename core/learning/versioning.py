"""
core/learning/versioning.py — Model Version Control & Rollback.

Evaluates newly trained models against holdout sets and automatically
rolls back if accuracy degrades. On a successful deployment, produces a
full DeploymentPackage via DeploymentPackager so the backend can push
it to firmware and track it in the deployment history.
"""

from __future__ import annotations

import structlog
import json
import time
from pathlib import Path
from typing import Any, Optional

from core.models.deployment_packager import DeploymentPackager

log = structlog.get_logger(__name__)

# If new model accuracy < (old model accuracy - margin), trigger rollback
ROLLBACK_MARGIN = 0.05


class ModelVersionControl:
    """Manages model versions, deployment, and rollback decisions."""

    def __init__(self, model_dir: Path, model_name: str, qnn: Any) -> None:
        self._model_dir  = model_dir
        self._model_name = model_name
        self._qnn        = qnn
        self._registry_path = model_dir / f"{model_name}_versions.json"
        self._packager   = DeploymentPackager(model_dir)

        self._registry: dict[str, Any] = self._load_registry()
        # Last successfully built package (None until first deployment)
        self.last_package: Optional[Any] = None

    def _load_registry(self) -> dict[str, Any]:
        if self._registry_path.exists():
            try:
                with open(self._registry_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"current_version": 1, "history": []}

    def _save_registry(self) -> None:
        with open(self._registry_path, "w") as f:
            json.dump(self._registry, f, indent=2)

    def evaluate_and_deploy(
        self,
        new_accuracy: float,
        previous_accuracy: float,
        dataset_version: str = "auto",
    ) -> bool:
        """
        Evaluate if the newly trained model is safe to deploy.

        Returns True (and stores `last_package`) if deployed,
        False if rolled back.
        """
        v = self._registry["current_version"]

        if new_accuracy < (previous_accuracy - ROLLBACK_MARGIN):
            log.warning(
                "versioning.rollback_triggered",
                new_acc=new_accuracy,
                prev_acc=previous_accuracy,
            )
            self._registry["history"].append({
                "version":   v + 1,
                "action":    "rolled_back",
                "accuracy":  new_accuracy,
                "timestamp": time.time(),
            })
            self._save_registry()
            self.last_package = None
            return False

        # Deploy — bump version and produce a proper deployment package
        new_v = v + 1
        self._registry["current_version"] = new_v
        self._registry["history"].append({
            "version":   new_v,
            "action":    "deployed",
            "accuracy":  new_accuracy,
            "timestamp": time.time(),
        })
        self._save_registry()

        # Build the deployment package (checksum + manifest + compatibility info)
        try:
            self.last_package = self._packager.pack(
                model_name         = self._model_name,
                accuracy           = new_accuracy,
                dataset_version    = dataset_version,
                deployment_version = new_v,
                source             = "learning_loop",
            )
        except Exception:
            log.exception("versioning.package_build_failed", version=new_v)
            self.last_package = None

        log.info(
            "versioning.deployed",
            version=new_v,
            acc=new_accuracy,
            package_id=self.last_package.package_id if self.last_package else None,
        )
        return True

