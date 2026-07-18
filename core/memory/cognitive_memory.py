# core/memory/cognitive_memory.py

from __future__ import annotations

import time
import structlog
from typing import Any, Dict, List, Optional

log = structlog.get_logger(__name__)


class MemoryCategory:
    """Base class representing a specific memory domain (e.g. Preferences)."""

    def __init__(self, name: str, max_entries: int = 100, max_age_s: float = 86400 * 7) -> None:
        self.name = name
        self.max_entries = max_entries
        self.max_age_s = max_age_s
        self.entries: List[Dict[str, Any]] = []

    def store(self, item: Dict[str, Any]) -> None:
        """Add item to memory store with timestamping and run GC."""
        record = {
            "data": item,
            "created_at": time.time(),
        }
        self.entries.append(record)
        self.garbage_collect()

    def retrieve(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve memories matching query criteria."""
        results = []
        for e in self.entries:
            matched = True
            for k, v in query.items():
                # Traverse nested data structure if needed
                if k in e["data"]:
                    if e["data"][k] != v:
                        matched = False
                        break
                else:
                    matched = False
                    break
            if matched:
                results.append(e["data"])
        return results

    def garbage_collect(self) -> None:
        """Prune expired or excess memory records."""
        now = time.time()
        # Prune by age
        self.entries = [
            e for e in self.entries
            if (now - e["created_at"]) <= self.max_age_s
        ]
        # Prune by capacity
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]


class CognitiveMemory:
    """
    Subsystem managing logical memory stores (Preference, Decision, etc.)
    with configurable category-level retention.
    """

    def __init__(self, max_entries: int = 100, max_age_days: int = 7) -> None:
        self._max_entries = max_entries
        self._max_age_s = max_age_days * 86400.0

        # Logical categories
        self.categories: Dict[str, MemoryCategory] = {
            "preference": MemoryCategory("preference", self._max_entries, self._max_age_s),
            "decision":   MemoryCategory("decision",   self._max_entries, self._max_age_s),
            "context":    MemoryCategory("context",    self._max_entries, self._max_age_s),
            "activity":   MemoryCategory("activity",   self._max_entries, self._max_age_s),
            "device":     MemoryCategory("device",     self._max_entries, self._max_age_s),
            "policy":     MemoryCategory("policy",     self._max_entries, self._max_age_s),
            "inference":  MemoryCategory("inference",  self._max_entries, self._max_age_s),
            "interaction":MemoryCategory("interaction",self._max_entries, self._max_age_s),
        }

    def store_memory(self, category: str, item: Dict[str, Any]) -> None:
        if category in self.categories:
            self.categories[category].store(item)
            log.debug("memory.stored", category=category)
        else:
            log.warning("memory.invalid_category", category=category)

    def query_memories(self, category: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        if category in self.categories:
            return self.categories[category].retrieve(query)
        return []

    def get_statistics(self) -> Dict[str, int]:
        """Return sizes of all memory stores."""
        return {cat: len(store.entries) for cat, store in self.categories.items()}
