"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import enum
import logging
from collections.abc import Callable
from functools import cached_property

from roborock.containers import HomeDataDevice, HomeDataProduct, UserData
from roborock.roborock_message import RoborockMessage

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "RoborockDevice",
    "DeviceVersion",
]


class DeviceVersion(enum.StrEnum):
    """Enum for device versions."""

    V1 = "1.0"
    A01 = "A01"
    UNKNOWN = "unknown"


class RoborockDevice:
    """Unified Roborock device class with automatic connection setup."""

    def __init__(
        self,
        user_data: UserData,
        device_info: HomeDataDevice,
        product_info: HomeDataProduct,
        mqtt_channel: MqttChannel,
    ) -> None:
        """Initialize the RoborockDevice.

        The device takes ownership of the MQTT channel for communication with the device.
        Use `connect()` to establish the connection, which will set up the MQTT channel
        for receiving messages from the device. Use `close()` to unsubscribe from the MQTT
        channel.
        """
        self._user_data = user_data
        self._device_info = device_info
        self._product_info = product_info
        self._mqtt_channel = mqtt_channel
        self._unsub: Callable[[], None] | None = None

    @property
    def duid(self) -> str:
        """Return the device unique identifier (DUID)."""
        return self._device_info.duid

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._device_info.name

    @cached_property
    def device_version(self) -> str:
        """Return the device version.

        At the moment this is a simple check against the product version (pv) of the device
        and used as a placeholder for upcoming functionality for devices that will behave
        differently based on the version and capabilities.
        """
        if self._device_info.pv == DeviceVersion.V1.value:
            return DeviceVersion.V1
        elif self._device_info.pv == DeviceVersion.A01.value:
            return DeviceVersion.A01
        _LOGGER.warning(
            "Unknown device version %s for device %s, using default UNKNOWN",
            self._device_info.pv,
            self._device_info.name,
        )
        return DeviceVersion.UNKNOWN

    async def connect(self) -> None:
        """Connect to the device using MQTT.

        This method will set up the MQTT channel for communication with the device.
        """
        if self._unsub:
            raise ValueError("Already connected to the device")
        self._unsub = await self._mqtt_channel.subscribe(self._on_mqtt_message)

    async def close(self) -> None:
        """Close the MQTT connection to the device.

        This method will unsubscribe from the MQTT channel and clean up resources.
        """
        if self._unsub:
            self._unsub()
            self._unsub = None

    def _on_mqtt_message(self, message: RoborockMessage) -> None:
        """Handle incoming MQTT messages from the device.

        This method should be overridden in subclasses to handle specific device messages.
        """
        _LOGGER.debug("Received message from device %s: %s", self.duid, message)
