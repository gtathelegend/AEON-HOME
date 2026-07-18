# backend/aeon/services/event_bus.py

from __future__ import annotations

import asyncio
import structlog
from typing import Any, Callable, Dict, List

log = structlog.get_logger(__name__)


class EventBus:
    """
    Decoupled Event Bus enabling loose coupling between backend services.
    Supports asynchronous and synchronous subscriber handlers.
    """

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[[Any], Any]]] = {}

    def subscribe(self, event_type: str, listener: Callable[[Any], Any]) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
        log.debug("event_bus.subscribed", event=event_type)

    async def publish(self, event_type: str, data: Any) -> None:
        log.info("event_bus.published", event=event_type)
        if event_type not in self._listeners:
            return
        
        tasks = []
        for listener in self._listeners[event_type]:
            if asyncio.iscoroutinefunction(listener):
                tasks.append(asyncio.create_task(listener(data)))
            else:
                try:
                    listener(data)
                except Exception as e:
                    log.error("event_bus.listener_error", event=event_type, error=str(e))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
