import asyncio
from typing import Callable, Awaitable

from bot.utils.logger.logger import logger


class EventDebouncer[K, E]:
    def __init__(self, wait_seconds: int, max_size: int):
        self.wait_seconds = wait_seconds
        self.max_size = max_size
        self.buffers: dict[K, list[E]] = {}
        self.tasks: dict[K, asyncio.Task] = {}

    async def add_event(self, key: K, event: E, callback: Callable[[list[E], K], Awaitable[None]]):
        if key not in self.buffers:
            self.buffers[key] = []
        self.buffers[key].append(event)

        if key in self.tasks and not self.tasks[key].done():
            self.tasks[key].cancel()

        if len(self.buffers[key]) >= self.max_size:
            await self._flush(key, callback)
        else:
            self.tasks[key] = asyncio.create_task(
                self._wait_and_flush(key, callback)
            )

    async def _flush(self, key: K, callback: Callable[[list[E], K], Awaitable[None]]):
        events = self.buffers.pop(key, [])
        self.tasks.pop(key, None)
        if events:
            await callback(events[:self.max_size], key)
            if len(events) > self.max_size:
                logger.warning(f"Too many events for key {key}: {len(events)}")
                await callback(events[self.max_size:], key)

    async def _wait_and_flush(self, key: K, callback: Callable[[list[E], K], Awaitable[None]]):
        try:
            await asyncio.sleep(self.wait_seconds)
            logger.debug(f"Flushing events for key {key} after waiting {self.wait_seconds} seconds")
            await self._flush(key, callback)
        except asyncio.CancelledError:
            pass
