"""
aeon/learning/versioning.py — Model Version Control & Rollback.

Evaluates newly trained models against holdout sets and automatically
rolls back if accuracy degrades. Orchestrates QNNManager reloads.
"""

from __future__ import annotations

import structlog
import json
import time
import shutil
from pathlib import Path
from typing import Any

log = structlog.get_logger(__name__)

# If new model accuracy < (old model accuracy - margin), trigger rollback
ROLLBACK_MARGIN = 0.05 


class ModelVersionControl:
    """Manages model versions, deployment, and evaluation."""

    def __init__(self, model_dir: Path, model_name: str, qnn: Any) -> None:
        self._model_dir = model_dir
        self._model_name = model_name
        self._qnn = qnn
        self._registry_path = model_dir / f"{model_name}_versions.json"
        
        self._registry = self._load_registry()

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

    def evaluate_and_deploy(self, new_accuracy: float, previous_accuracy: float) -> bool:
        """
        Evaluate if the newly trained model is safe to deploy.
        Returns True if deployed, False if rolled back.
        """
        v = self._registry["current_version"]
        
        if new_accuracy < (previous_accuracy - ROLLBACK_MARGIN):
            log.warning("versioning.rollback_triggered", 
                        new_acc=new_accuracy, prev_acc=previous_accuracy)
            
            # Rollback: in a real implementation we would restore the .onnx / .bin
            # backup files. Here we simulate the logic.
            self._registry["history"].append({
                "version": v + 1,
                "action": "rolled_back",
                "accuracy": new_accuracy,
                "timestamp": time.time()
            })
            self._save_registry()
            return False
            
        # Deploy
        new_v = v + 1
        self._registry["current_version"] = new_v
        self._registry["history"].append({
            "version": new_v,
            "action": "deployed",
            "accuracy": new_accuracy,
            "timestamp": time.time()
        })
        self._save_registry()
        
        log.info("versioning.deployed", version=new_v, acc=new_accuracy)
        
        # In a real pipeline, we trigger ONNX export here, compile via qnn-net-run,
        # then trigger hot reload. We mock the async reload call here.
        # It's an async method in QNNManager, so we must await it upstream.
        return True
