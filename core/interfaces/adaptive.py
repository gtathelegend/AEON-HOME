# core/interfaces/adaptive.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


class IContextProvider(ABC):
    @abstractmethod
    async def get_context(self) -> Dict[str, Any]:
        """Collect and return context contribution from this provider."""
        pass


class IContextEngine(ABC):
    @abstractmethod
    async def get_current_context(self) -> Dict[str, Any]:
        """Retrieve the latest unified frozen context snapshot."""
        pass

    @abstractmethod
    def register_provider(self, category: str, provider: IContextProvider) -> None:
        """Register a new context provider dynamically."""
        pass


class IActivityProvider(ABC):
    @abstractmethod
    async def infer_activity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Infer activity payload from context."""
        pass


class IActivityEngine(ABC):
    @abstractmethod
    async def infer_current_activity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the activity inference pipeline using context."""
        pass

    @abstractmethod
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the rolling activity history."""
        pass


class IProfileStore(ABC):
    @abstractmethod
    async def load_profile(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def save_profile(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        pass


class IProfileEngine(ABC):
    @abstractmethod
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def record_signal(self, user_id: str, setting: str, value: Any, source: str) -> None:
        """Record manual overrides or behavior corrections as training signals."""
        pass


class IPolicy(ABC):
    @property
    @abstractmethod
    def identifier(self) -> str:
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority level integer (higher value = higher priority)."""
        pass

    @abstractmethod
    async def evaluate(self, context: Dict[str, Any], activity: Dict[str, Any], profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate policy conditions. Returns action dictionary or None."""
        pass


class IPolicyEngine(ABC):
    @abstractmethod
    async def evaluate_policies(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
        system_state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run the conflict-resolution evaluation pipeline and return a final Decision object."""
        pass


class IDecisionPublisher(ABC):
    @abstractmethod
    async def publish(self, decision: Dict[str, Any]) -> None:
        pass
