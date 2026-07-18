# core/interfaces/logger.py

from abc import ABC, abstractmethod

class ILogger(ABC):
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        pass

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        pass

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        pass

    @abstractmethod
    def exception(self, message: str, **kwargs) -> None:
        pass
