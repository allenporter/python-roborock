"""Tests for the Roborock Local Client V1."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import Mock, patch
import warnings

import pytest
import syrupy

from roborock import HomeData
from roborock.data import DeviceData, RoomMapping
from roborock.exceptions import RoborockException
from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.version_1_apis.roborock_local_client_v1 import RoborockLocalClientV1
from tests.fixtures.logging import CapturedRequestLog
from tests.mock_data import HOME_DATA_RAW, TEST_LOCAL_API_HOST

from .mock_data import LOCAL_KEY

_LOGGER = logging.getLogger(__name__)

pytest_plugins = [
    "tests.fixtures.logging_fixtures",
]

QUEUE_TIMEOUT = 10

LocalRequestHandler = Callable[[bytes], bytes | None]


@pytest.fixture(name="local_received_requests")
def received_requests_fixture() -> Queue[bytes]:
    """Fixture that provides access to the received requests."""
    return Queue()


@pytest.fixture(name="local_response_queue")
def response_queue_fixture() -> Generator[Queue[bytes], None, None]:
    """Fixture that provides a queue for enqueueing responses to be sent back to the client under test."""
    response_queue: Queue[bytes] = Queue()
    yield response_queue
    if not response_queue.empty():
        warnings.warn("Not all fake responses were consumed")


@pytest.fixture(name="local_request_handler")
def local_request_handler_fixture(
    local_received_requests: Queue[bytes], local_response_queue: Queue[bytes]
) -> LocalRequestHandler:
    """Fixture records incoming requests and replies with responses from the queue."""

    def handle_request(client_request: bytes) -> bytes | None:
        """Handle an incoming request from the client."""
        local_received_requests.put(client_request)

        # Insert a prepared response into the response buffer
        if not local_response_queue.empty():
            return local_response_queue.get()
        return None

    return handle_request


@pytest.fixture(name="mock_create_local_connection")
def create_local_connection_fixture(
    local_request_handler: LocalRequestHandler, log: CapturedRequestLog
) -> Generator[None, None, None]:
    """Fixture that overrides the transport creation to wire it up to the mock socket."""

    async def create_connection(protocol_factory: Callable[[], asyncio.Protocol], *args) -> tuple[Any, Any]:
        protocol = protocol_factory()

        def handle_write(data: bytes) -> None:
            _LOGGER.debug("Received: %s", data)
            response = local_request_handler(data)
            log.add_log_entry("[local >]", data)
            if response is not None:
                _LOGGER.debug("Replying with %s", response)
                log.add_log_entry("[local <]", response)
                loop = asyncio.get_running_loop()
                loop.call_soon(protocol.data_received, response)

        closed = asyncio.Event()

        mock_transport = Mock()
        mock_transport.write = handle_write
        mock_transport.close = closed.set
        mock_transport.is_reading = lambda: not closed.is_set()

        return (mock_transport, "proto")

    with patch("roborock.version_1_apis.roborock_local_client_v1.get_running_loop") as mock_loop:
        mock_loop.return_value.create_connection.side_effect = create_connection
        yield


@pytest.fixture(name="local_client")
async def local_client_fixture(mock_create_local_connection: None) -> AsyncGenerator[RoborockLocalClientV1, None]:
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
        host=TEST_LOCAL_API_HOST,
    )
    client = RoborockLocalClientV1(device_info, queue_timeout=QUEUE_TIMEOUT)
    try:
        yield client
    finally:
        if not client.is_connected():
            try:
                await client.async_release()
            except Exception:
                pass


def build_rpc_response(seq: int, message: dict[str, Any]) -> bytes:
    """Build an encoded RPC response message."""
    return build_raw_response(
        protocol=RoborockMessageProtocol.GENERAL_REQUEST,
        seq=seq,
        payload=json.dumps(
            {
                "dps": {102: json.dumps(message)},
            }
        ).encode(),
    )


def build_raw_response(protocol: RoborockMessageProtocol, seq: int, payload: bytes) -> bytes:
    """Build an encoded RPC response message."""
    message = RoborockMessage(
        protocol=protocol,
        random=23,
        seq=seq,
        payload=payload,
    )
    return MessageParser.build(message, local_key=LOCAL_KEY)


async def test_async_connect(
    local_client: RoborockLocalClientV1,
    local_received_requests: Queue,
    local_response_queue: Queue,
    snapshot: syrupy.SnapshotAssertion,
    log: CapturedRequestLog,
) -> None:
    """Test that we can connect to the Roborock device."""
    local_response_queue.put(build_raw_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, b"ignored"))
    local_response_queue.put(build_raw_response(RoborockMessageProtocol.PING_RESPONSE, 2, b"ignored"))

    await local_client.async_connect()
    assert local_client.is_connected()
    assert local_received_requests.qsize() == 2

    await local_client.async_disconnect()
    assert not local_client.is_connected()

    assert snapshot == log


@pytest.fixture(name="connected_local_client")
async def connected_local_client_fixture(
    local_response_queue: Queue,
    local_client: RoborockLocalClientV1,
) -> AsyncGenerator[RoborockLocalClientV1, None]:
    local_response_queue.put(build_raw_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, b"ignored"))
    local_response_queue.put(build_raw_response(RoborockMessageProtocol.PING_RESPONSE, 2, b"ignored"))
    await local_client.async_connect()
    yield local_client


async def test_get_room_mapping(
    local_received_requests: Queue,
    local_response_queue: Queue,
    connected_local_client: RoborockLocalClientV1,
    snapshot: syrupy.SnapshotAssertion,
    log: CapturedRequestLog,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""

    test_request_id = 5050

    message = build_rpc_response(
        seq=test_request_id,
        message={
            "id": test_request_id,
            "result": [[16, "2362048"], [17, "2362044"]],
        },
    )
    local_response_queue.put(message)

    with patch("roborock.protocols.v1_protocol.get_next_int", return_value=test_request_id):
        room_mapping = await connected_local_client.get_room_mapping()

    assert room_mapping == [
        RoomMapping(segment_id=16, iot_id="2362048"),
        RoomMapping(segment_id=17, iot_id="2362044"),
    ]

    assert snapshot == log


async def test_retry_request(
    local_received_requests: Queue,
    local_response_queue: Queue,
    connected_local_client: RoborockLocalClientV1,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""

    test_request_id = 5050

    retry_message = build_rpc_response(
        seq=test_request_id,
        message={
            "id": test_request_id,
            "result": "retry",
        },
    )
    local_response_queue.put(retry_message)

    with (
        patch("roborock.protocols.v1_protocol.get_next_int", return_value=test_request_id),
        pytest.raises(RoborockException, match="Device is busy, try again later"),
    ):
        await connected_local_client.get_room_mapping()
