"""Traits for B01 devices."""

from roborock.devices.b01_channel import send_decoded_command
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait

from .props import B01PropsApi

__init__ = [
    "create_b01_traits",
    "B01PropsApi",
]


def create_b01_traits(channel: MqttChannel) -> list[Trait]:
    """Create traits for B01 devices."""
    return [B01PropsApi(channel)]
