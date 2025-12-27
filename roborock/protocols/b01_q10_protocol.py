"""Roborock B01 Protocol encoding and decoding."""

import json
import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)

_LOGGER = logging.getLogger(__name__)

B01_VERSION = b"B01"
ParamsType = list | dict | int | None


def encode_mqtt_payload(command: B01_Q10_DP, params: ParamsType) -> RoborockMessage:
    """Encode payload for B01 commands over MQTT."""
    dps_data = {
        "dps": {
            command.code: params,
        }
    }
    # payload = pad(json.dumps(dps_data).encode("utf-8"), AES.block_size)
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        version=B01_VERSION,
        payload=json.dumps(dps_data).encode("utf-8"),
    )


def _convert_datapoints(datapoints: dict[str, Any], message: RoborockMessage) -> dict[B01_Q10_DP, Any]:
    """Convert the 'dps' dictionary keys from strings to B01_Q10_DP enums."""
    result = {}
    for key, value in datapoints.items():
        if not isinstance(key, str):
            raise RoborockException(f"Invalid B01 message format: 'dps' keys should be strings for {message.payload!r}")
        dps = B01_Q10_DP.from_code(int(key))
        result[dps] = value
    return result


def decode_rpc_response(message: RoborockMessage) -> dict[B01_Q10_DP, Any]:
    """Decode a B01 RPC_RESPONSE message."""
    if not message.payload:
        raise RoborockException("Invalid B01 message format: missing payload")
    try:
        payload = json.loads(message.payload.decode())
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as e:
        raise RoborockException(f"Invalid B01 message payload: {e} for {message.payload!r}") from e

    datapoints = payload.get("dps", {})
    if not isinstance(datapoints, dict):
        raise RoborockException(f"Invalid B01 message format: 'dps' should be a dictionary for {message.payload!r}")

    result = _convert_datapoints(datapoints, message)
    # The COMMON response contains nested datapoints that also need conversion
    if common_result := result.get(B01_Q10_DP.COMMON):
        common_dps_result = _convert_datapoints(common_result, message)
        result[B01_Q10_DP.COMMON] = common_dps_result
    return result
