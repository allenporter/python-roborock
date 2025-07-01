"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import enum
import logging
from functools import cached_property

from roborock.containers import HomeDataDevice, HomeDataProduct, UserData

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

        The device takes ownership of the MQTT channel for communication with the device
        and will close it when the device is closed.
        """
        self._user_data = user_data
        self._device_info = device_info
        self._product_info = product_info
        self._mqtt_channel = mqtt_channel

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
        await self._mqtt_channel.subscribe(self._on_mqtt_message)

    async def close(self) -> None:
        """Close the MQTT connection to the device.

        This method will unsubscribe from the MQTT channel and clean up resources.
        """
        await self._mqtt_channel.close()

    def _on_mqtt_message(self, message: bytes) -> None:
        """Handle incoming MQTT messages from the device.

        This method should be overridden in subclasses to handle specific device messages.
        """
        _LOGGER.debug("Received message from device %s: %s", self.duid, message[:50])  # Log first 50 bytes for brevity
