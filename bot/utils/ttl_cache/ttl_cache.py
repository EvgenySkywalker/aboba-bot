import time
from collections import OrderedDict

from bot.utils.logger.logger import logger


class TtlCache:
    """LRU cache of descriptions by event ID with TTL."""

    def __init__(self, max_size: int = 10, ttl: float = 300.0):
        self._data: "OrderedDict" = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def get(self, event_id: str) -> str | None:
        item = self._data.get(event_id)

        if item is None:
            return None

        value, expires_at = item
        if time.monotonic() >= expires_at:
            del self._data[event_id]
            return None

        self._data.move_to_end(event_id)

        logger.debug(f"Got cache for {event_id}")
        return value

    def put(self, event_id: str, value: str) -> None:
        while len(self._data) >= self._max_size:
            self._data.popitem(last=False)
        self._data[event_id] = (value, time.monotonic() + self._ttl)
        logger.debug(f"Cached {event_id} for {self._ttl} seconds")
