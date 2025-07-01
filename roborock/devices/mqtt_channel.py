import logging
from collections.abc import Callable

from roborock.containers import RRiot
from roborock.mqtt.session import MqttParams, MqttSession

_LOGGER = logging.getLogger(__name__)


class MqttChannel:
    """RPC-style channel for communicating with a specific device over MQTT.

    This currently only supports listening to messages and does not yet
    support RPC functionality.
    """

    def __init__(self, mqtt_session: MqttSession, duid: str, rriot: RRiot, mqtt_params: MqttParams):
        self._mqtt_session = mqtt_session
        self._duid = duid
        self._rriot = rriot
        self._mqtt_params = mqtt_params
        self._unsub: Callable[[], None] | None = None

    @property
    def _publish_topic(self) -> str:
        """Topic to send commands to the device."""
        return f"rr/m/i/{self._rriot.u}/{self._mqtt_params.username}/{self._duid}"

    @property
    def _subscribe_topic(self) -> str:
        """Topic to receive responses from the device."""
        return f"rr/m/o/{self._rriot.u}/{self._mqtt_params.username}/{self._duid}"

    async def subscribe(self, callback: Callable[[bytes], None]) -> None:
        """Subscribe to the device's response topic."""
        if self._unsub:
            raise ValueError("Already subscribed to the response topic")
        self._unsub = await self._mqtt_session.subscribe(self._subscribe_topic, callback)

    async def close(self) -> None:
        """Close the MQTT subscription."""
        if self._unsub:
            self._unsub()
            self._unsub = None
