# core/interfaces/repository.py

from abc import ABC, abstractmethod
from typing import Any, List, Dict
from datetime import datetime

class IRepository(ABC):
    @abstractmethod
    async def log_feature(self, frame: Any) -> None:
        pass

    @abstractmethod
    async def log_decision(self, decision: Any) -> None:
        pass

    @abstractmethod
    async def log_event(self, category: str, name: str, payload: dict) -> None:
        pass

    @abstractmethod
    async def label_decision(self, decision_id: int, label: int) -> None:
        pass

    @abstractmethod
    async def get_labelled_samples(self, since: datetime, limit: int = 1000) -> List[Dict]:
        pass

    @abstractmethod
    async def get_recent_events(self, limit: int = 50) -> List[Dict]:
        pass

    @abstractmethod
    async def get_sensor_history(self, minutes: int = 60) -> List[Dict]:
        pass
