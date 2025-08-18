"""Module for managing pending RPCs."""

import asyncio
import logging
from typing import Generic, TypeVar

from roborock.exceptions import RoborockException

_LOGGER = logging.getLogger(__name__)


K = TypeVar("K")
V = TypeVar("V")


class PendingRpcs(Generic[K, V]):
    """Manage pending RPCs."""

    def __init__(self) -> None:
        """Initialize the pending RPCs."""
        self._queue_lock = asyncio.Lock()
        self._waiting_queue: dict[K, asyncio.Future[V]] = {}

    async def start(self, key: K) -> asyncio.Future[V]:
        """Start the pending RPCs."""
        future: asyncio.Future[V] = asyncio.Future()
        async with self._queue_lock:
            if key in self._waiting_queue:
                raise RoborockException(f"Request ID {key} already pending, cannot send command")
            self._waiting_queue[key] = future
        return future

    async def pop(self, key: K) -> None:
        """Pop a pending RPC."""
        async with self._queue_lock:
            if (future := self._waiting_queue.pop(key, None)) is not None:
                future.cancel()

    async def resolve(self, key: K, value: V) -> None:
        """Resolve waiting future with proper locking."""
        async with self._queue_lock:
            if (future := self._waiting_queue.pop(key, None)) is not None:
                future.set_result(value)
            else:
                _LOGGER.debug("Received unsolicited message: %s", key)
