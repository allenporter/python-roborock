"""Thin wrapper around the MQTT channel for Roborock A01 devices."""

import asyncio
import logging
from typing import Any, overload

from roborock.exceptions import RoborockException
from roborock.protocols.a01_protocol import (
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockZeoProtocol,
)

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0


@overload
async def send_decoded_command(
    mqtt_channel: MqttChannel,
    params: dict[RoborockDyadDataProtocol, Any],
) -> dict[RoborockDyadDataProtocol, Any]:
    ...


@overload
async def send_decoded_command(
    mqtt_channel: MqttChannel,
    params: dict[RoborockZeoProtocol, Any],
) -> dict[RoborockZeoProtocol, Any]:
    ...


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    params: dict[RoborockDyadDataProtocol, Any] | dict[RoborockZeoProtocol, Any],
) -> dict[RoborockDyadDataProtocol, Any] | dict[RoborockZeoProtocol, Any]:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending MQTT command: %s", params)
    roborock_message = encode_mqtt_payload(params)

    # We only block on a response for queries
    param_values = {int(k): v for k, v in params.items()}
    if not (
        query_values := param_values.get(int(RoborockDyadDataProtocol.ID_QUERY))
        or param_values.get(int(RoborockZeoProtocol.ID_QUERY))
    ):
        await mqtt_channel.publish(roborock_message)
        return {}

    # This can be simplified if we can assume a all results are returned in 
    # single response. Otherwise, this will construct a result by merging in
    # responses that contain the ids that were queried.
    finished = asyncio.Event()
    result: dict[int, Any] = {}

    def find_response(response_message: RoborockMessage) -> None:
        """Handle incoming messages and resolve the future."""
        try:
            decoded = decode_rpc_response(response_message)
        except RoborockException:
            return
        for key, value in decoded.items():
            if key in query_values:
                result[key] = value
        if len(result) != len(query_values):
            return
        _LOGGER.debug("Received query response: %s", result)
        if not finished.is_set():
            finished.set()

    unsub = await mqtt_channel.subscribe(find_response)

    try:
        await mqtt_channel.publish(roborock_message)
        try:
            await asyncio.wait_for(finished.wait(), timeout=_TIMEOUT)
        except TimeoutError as ex:
            raise RoborockException(f"Command timed out after {_TIMEOUT}s") from ex
    finally:
        unsub()

    return result  # type: ignore[return-value]
