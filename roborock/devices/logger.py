"""Logger adapter for device-specific logging."""

import logging
from collections.abc import MutableMapping
from typing import Any


class DeviceLoggerAdapter(logging.LoggerAdapter):
    """A LoggerAdapter that prepends a [DUID] prefix to all messages."""

    def __init__(self, logger: logging.Logger, duid: str):
        # The 'extra' dictionary can hold any custom context you need.
        # We define a custom 'prefix' key here.
        super().__init__(logger, {"prefix": duid})

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        """Format the message by adding the device prefix."""
        return f"{self.extra['prefix']} {msg}", kwargs  # type: ignore[index]
