from __future__ import annotations

import asyncio
import base64
import logging
import threading
import typing
import uuid
from asyncio import Lock
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from .api import KEEPALIVE, RoborockClient
from .containers import DeviceData, UserData
from .exceptions import RoborockException, VacuumError
from .protocol import MessageParser, Utils, md5hex
from .roborock_future import RoborockFuture
from .util import RoborockLoggerAdapter

if typing.TYPE_CHECKING:
    pass
_LOGGER = logging.getLogger(__name__)
CONNECT_REQUEST_ID = 0
DISCONNECT_REQUEST_ID = 1


class MqttClient(mqtt.Client):
    """Implementation of the MQTT client.

    This class exists to manage internals of the client.
    """

    _thread: threading.Thread
    _client_id: str

    def __init__(self, logger: RoborockLoggerAdapter) -> None:
        """Initialize the mqtt client."""
        super().__init__(protocol=mqtt.MQTTv5)
        self._logger = logger
        self.update_client_id()

    def update_client_id(self):
        self._client_id = mqtt.base62(uuid.uuid4().int, padding=22)

    def ensure_loop_started(self) -> None:
        """Restart the loop if it is inactive."""
        if self._thread and self._thread.is_alive():
            _LOGGER.debug("Mqtt loop already running")
            return
        if self._thread:
            self._logger.debug("Stopping mqtt loop")
            super().loop_stop()
        super().loop_start()
        self._logger.debug("mqtt loop has been started")


class RoborockMqttClient(RoborockClient):
    def __init__(self, user_data: UserData, device_info: DeviceData, queue_timeout: int = 10) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()
        RoborockClient.__init__(self, endpoint, device_info, queue_timeout)
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)
        self._mqtt_user = rriot.u
        self._hashed_user = md5hex(self._mqtt_user + ":" + rriot.k)[2:10]
        url = urlparse(rriot.r.m)
        if not isinstance(url.hostname, str):
            raise RoborockException("Url parsing returned an invalid hostname")
        self._mqtt_host = str(url.hostname)
        self._mqtt_port = url.port
        self._mqtt_ssl = url.scheme == "ssl"
        self._mqtt_password = rriot.s
        self._hashed_password = md5hex(self._mqtt_password + ":" + rriot.k)[16:]
        self._endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._connection_lock = Lock()

        # Initialize the MQQ client library and set up callbacks
        client = MqttClient(self._logger)
        if self._mqtt_ssl:
            client.tls_set()
        client.username_pw_set(self._hashed_user, self._hashed_password)
        client.on_connect = self._mqtt_on_connect
        client.on_message = self._mqtt_on_message
        client.on_disconnect = self._mqtt_on_disconnect
        self._mqtt_client = client

    def _mqtt_on_connect(self, *args, **kwargs):
        _, __, ___, rc, ____ = args
        connection_queue = self._waiting_queue.get(CONNECT_REQUEST_ID)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            message = f"Failed to connect ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(message)))
            return
        self._logger.info(f"Connected to mqtt {self._mqtt_host}:{self._mqtt_port}")
        topic = f"rr/m/o/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}"
        (result, _) = self._mqtt_client.subscribe(topic)
        if result != 0:
            message = f"Failed to subscribe ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(message)))
            return
        self._logger.info(f"Subscribed to topic {topic}")
        if connection_queue:
            connection_queue.resolve((True, None))

    def _mqtt_on_message(self, *args, **kwargs):
        client, __, msg = args
        try:
            messages, _ = MessageParser.parse(msg.payload, local_key=self.device_info.device.local_key)
            super()._on_message_received(messages)
        except Exception as ex:
            self._logger.exception(ex)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        _, __, rc, ___ = args
        try:
            exc = RoborockException(mqtt.error_string(rc)) if rc != mqtt.MQTT_ERR_SUCCESS else None
            super()._on_connection_lost(exc)
            if rc == mqtt.MQTT_ERR_PROTOCOL:
                self._mqtt_client.update_client_id()
            connection_queue = self._waiting_queue.get(DISCONNECT_REQUEST_ID)
            if connection_queue:
                connection_queue.resolve((True, None))
        except Exception as ex:
            self._logger.exception(ex)

    async def async_disconnect(self) -> None:
        async with self._connection_lock:
            if not self._mqtt_client.is_connected():
                return

            self._logger.info("Disconnecting from mqtt")
            disconnected_future = asyncio.ensure_future(self._async_response(DISCONNECT_REQUEST_ID))
            rc = self._mqtt_client.disconnect()

            if rc == mqtt.MQTT_ERR_NO_CONN:
                disconnected_future.cancel()
                return

            if rc != mqtt.MQTT_ERR_SUCCESS:
                disconnected_future.cancel()
                raise RoborockException(f"Failed to disconnect ({mqtt.error_string(rc)})")

            (_, err) = await disconnected_future
            if err:
                raise RoborockException(err) from err

    async def async_connect(self) -> None:
        async with self._connection_lock:
            if self._mqtt_client.is_connected():
                self._mqtt_client.ensure_loop_started()
                return

            if self._mqtt_port is None or self._mqtt_host is None:
                raise RoborockException("Mqtt information was not entered. Cannot connect.")

            self._logger.debug("Connecting to mqtt")
            connected_future = asyncio.ensure_future(self._async_response(CONNECT_REQUEST_ID))
            self._mqtt_client.connect(host=self._mqtt_host, port=self._mqtt_port, keepalive=KEEPALIVE)
            self._mqtt_client.ensure_loop_started()
            (_, err) = await connected_future
            if err:
                raise RoborockException(err) from err

    def _send_msg_raw(self, msg: bytes) -> None:
        info = self._mqtt_client.publish(
            f"rr/m/i/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}", msg
        )
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RoborockException(f"Failed to publish ({mqtt.error_string(info.rc)})")
