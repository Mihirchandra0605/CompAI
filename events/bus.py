"""Async in-process event bus. Migrates to Kafka/Redis Streams in V2."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from .base import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class AsyncEventBus:
    """
    V1 event bus — in-process, asyncio-based.

    Migration path to V2:
    - Replace with KafkaEventBus or RedisStreamEventBus
    - Same publish/subscribe interface
    - Handlers become consumer group workers
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[DomainEvent] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to events by type. Supports wildcard: 'compliance.*'"""
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event."""
        await self._queue.put(event)

    async def start(self) -> None:
        """Start the event processing loop."""
        self._running = True
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        """Stop the event bus gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event bus error: {e}")

    async def _dispatch(self, event: DomainEvent) -> None:
        """Dispatch event to all matching handlers."""
        handlers: list[EventHandler] = []

        # Exact match
        handlers.extend(self._handlers.get(event.event_type, []))

        # Wildcard match
        for pattern, pattern_handlers in self._handlers.items():
            if pattern.endswith("*") and event.event_type.startswith(pattern[:-1]):
                handlers.extend(pattern_handlers)

        if handlers:
            results = await asyncio.gather(
                *(handler(event) for handler in handlers),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Event handler error: {result}")
