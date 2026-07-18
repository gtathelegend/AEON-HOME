# core/interfaces/storage.py

from abc import ABC, abstractmethod
from typing import Any, Tuple, List

class IStorage(ABC):
    @abstractmethod
    async def init(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class ICheckpointStore(ABC):
    @abstractmethod
    async def save_checkpoint(self, checkpoint_id: int, state: Any) -> None:
        pass

    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: int) -> Any:
        pass
