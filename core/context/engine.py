# core/context/engine.py

from __future__ import annotations

import structlog
from typing import Any, Dict

from core.interfaces.adaptive import IContextEngine, IContextProvider
from core.context.aggregator import ContextAggregator, ImmutableContext

log = structlog.get_logger(__name__)


class ContextEngine(IContextEngine):
    """
    Constructs a complete environmental, temporal, and user context.
    Executes the lifecycle: Collect -> Normalize -> Merge -> Validate -> Freeze -> Publish.
    """

    def __init__(self, ws_bus: Any = None) -> None:
        self._ws_bus = ws_bus
        self._providers: Dict[str, IContextProvider] = {}
        self._aggregator = ContextAggregator()
        self._manual_overrides: Dict[str, Any] = {}
        self._current_context: ImmutableContext = ImmutableContext()

    def register_provider(self, category: str, provider: IContextProvider) -> None:
        self._providers[category] = provider
        log.info("context.provider_registered", category=category)

    async def get_current_context(self) -> Dict[str, Any]:
        """Runs the lifecycle, caches the frozen context, and returns its dict form."""
        self._current_context = await self._aggregator.aggregate(
            providers=self._providers,
            overrides=self._manual_overrides,
        )
        return self._current_context.to_dict()

    async def record_manual_override(self, target: str, value: Any) -> None:
        """Record manual overrides to include in behavioral context."""
        self._manual_overrides[target] = value
        log.info("context.manual_override_recorded", target=target, value=value)
        # Update and publish context immediately
        ctx = await self.get_current_context()
        await self._publish_context(ctx)

    async def publish_current_context(self) -> None:
        """Build, freeze, and publish context to real-time bus."""
        ctx = await self.get_current_context()
        await self._publish_context(ctx)

    async def _publish_context(self, ctx_dict: Dict[str, Any]) -> None:
        if self._ws_bus:
            try:
                await self._ws_bus.publish("context_update", ctx_dict)
            except Exception:
                log.exception("context.publish_error")
        log.debug("context.published", temporal=ctx_dict.get("temporal"))
