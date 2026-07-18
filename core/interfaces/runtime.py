# core/interfaces/runtime.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Callable

class IInferenceRuntime(ABC):
    @abstractmethod
    async def infer(self, model_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class IModelLoader(ABC):
    @abstractmethod
    def load(self, model_name: str) -> Any:
        pass


class IScheduler(ABC):
    @abstractmethod
    async def schedule(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        pass
