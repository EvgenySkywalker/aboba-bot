import asyncio


class TimedRateLimiter:
    def __init__(self, max_calls: int, period_seconds: int):
        self.semaphore = asyncio.Semaphore(max_calls)
        self.period_seconds = period_seconds
        self._background_tasks: set[asyncio.Task] = set()

    async def _release_later(self) -> None:
        try:
            await asyncio.sleep(self.period_seconds)
        finally:
            self.semaphore.release()

    async def __aenter__(self):
        await self.semaphore.acquire()

        task = asyncio.create_task(self._release_later())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
