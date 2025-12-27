"""Tests for the B01 protocol message encoding and decoding."""

import json
import pathlib
from collections.abc import Generator
from typing import Any

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from freezegun import freeze_time
from syrupy import SnapshotAssertion

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.protocols.b01_q10_protocol import (
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TESTDATA_PATH = pathlib.Path("tests/protocols/testdata/b01_protocol/q10")
TESTDATA_FILES = list(TESTDATA_PATH.glob("*.json"))
TESTDATA_IDS = [x.stem for x in TESTDATA_FILES]


@pytest.fixture(autouse=True)
def fixed_time_fixture() -> Generator[None, None, None]:
    """Fixture to freeze time for predictable request IDs."""
    with freeze_time("2025-01-20T12:00:00"):
        yield


@pytest.mark.parametrize("filename", TESTDATA_FILES, ids=TESTDATA_IDS)
def test_decode_rpc_payload(filename: str, snapshot: SnapshotAssertion) -> None:
    """Test decoding a B01 RPC response protocol message."""
    with open(filename, "rb") as f:
        payload = f.read()

    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=payload,
        seq=12750,
        version=b"B01",
        random=97431,
        timestamp=1652547161,
    )

    decoded_message = decode_rpc_response(message)
    assert json.dumps(decoded_message, indent=2) == snapshot


@pytest.mark.parametrize(
    ("command", "params"),
    [
        (B01_Q10_DP.REQUETDPS, {}),
    ],
)
def test_encode_mqtt_payload(command: B01_Q10_DP, params: dict[str, Any]) -> None:
    """Test encoding of MQTT payload for B01 commands."""

    message = encode_mqtt_payload(command, params)
    assert isinstance(message, RoborockMessage)
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"B01"
    assert message.payload is not None
    unpadded = unpad(message.payload, AES.block_size)
    decoded_json = json.loads(unpadded.decode("utf-8"))

    assert decoded_json == {"dps": {"102": {}}}
