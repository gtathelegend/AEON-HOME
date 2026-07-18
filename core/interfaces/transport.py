# core/interfaces/transport.py

from abc import ABC, abstractmethod
from typing import Any

class ITransport(ABC):
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    async def publish(self, topic: str, payload: Any) -> None:
        pass
