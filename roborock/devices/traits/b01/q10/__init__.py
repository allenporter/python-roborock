"""Traits for Q10 B01 devices."""

import asyncio
import logging
from typing import Any

from roborock import B01Props
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel

from .command import CommandTrait
from .vacuum import VacuumTrait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "Q10PropertiesApi",
]


class Q10PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    command: CommandTrait
    """Trait for sending commands to Q10 devices."""

    vacuum: VacuumTrait
    """Trait for sending Vacuum related commands to Q10 devices"""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self.command = CommandTrait(channel)
        self.vacuum = VacuumTrait(self.command)
        self._channel = channel
        self._task: asyncio.Task | None = None


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)
