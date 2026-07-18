# core/interfaces/device.py

from abc import ABC, abstractmethod
from typing import Any, Dict

class IDevice(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def type(self) -> str:
        pass

    @property
    @abstractmethod
    def status(self) -> str:
        pass

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        pass
