"""End-to-end tests for LocalChannel using fake sockets."""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest

from roborock.devices.local_channel import LocalChannel
from roborock.protocol import create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.mock_data import LOCAL_KEY

TEST_HOST = "192.168.1.100"
TEST_DEVICE_UID = "test_device_uid"
TEST_CONNECT_NONCE = 12345
TEST_ACK_NONCE = 67890
TEST_RANDOM = 13579


@pytest.fixture(name="local_channel")
async def local_channel_fixture(mock_async_create_local_connection: None) -> AsyncGenerator[LocalChannel, None]:
    with patch(
        "roborock.devices.local_channel.get_next_int", return_value=TEST_CONNECT_NONCE, device_uid=TEST_DEVICE_UID
    ):
        channel = LocalChannel(host=TEST_HOST, local_key=LOCAL_KEY, device_uid=TEST_DEVICE_UID)
        yield channel
        channel.close()


def build_response(
    protocol: RoborockMessageProtocol,
    seq: int,
    payload: bytes,
    random: int,
) -> bytes:
    """Build an encoded response message."""
    if protocol == RoborockMessageProtocol.HELLO_RESPONSE:
        encoder = create_local_encoder(local_key=LOCAL_KEY, connect_nonce=TEST_CONNECT_NONCE, ack_nonce=None)
    else:
        encoder = create_local_encoder(local_key=LOCAL_KEY, connect_nonce=TEST_CONNECT_NONCE, ack_nonce=TEST_ACK_NONCE)

    msg = RoborockMessage(
        protocol=protocol,
        random=random,
        seq=seq,
        payload=payload,
    )
    return encoder(msg)


async def test_connect(
    local_channel: LocalChannel,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
) -> None:
    """Test connecting to the device."""
    # Queue HELLO response with payload to ensure it can be parsed
    local_response_queue.put_nowait(
        build_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, payload=b"ok", random=TEST_RANDOM)
    )

    await local_channel.connect()

    assert local_channel.is_connected
    assert local_received_requests.qsize() == 1

    # Verify HELLO request
    request_bytes = await local_received_requests.get()
    # Note: We cannot use create_local_decoder here because HELLO_REQUEST has payload=None
    # which causes MessageParser to fail parsing. For now we verify the raw bytes.

    # Protocol is at offset 19 (2 bytes)
    # Prefix(4) + Version(3) + Seq(4) + Random(4) + Timestamp(4) = 19
    assert len(request_bytes) >= 21
    protocol_bytes = request_bytes[19:21]
    assert int.from_bytes(protocol_bytes, "big") == RoborockMessageProtocol.HELLO_REQUEST


async def test_send_command(
    local_channel: LocalChannel,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
) -> None:
    """Test sending a command."""
    # Queue HELLO response
    local_response_queue.put_nowait(
        build_response(RoborockMessageProtocol.HELLO_RESPONSE, 1, payload=b"ok", random=TEST_RANDOM)
    )

    await local_channel.connect()

    # Clear requests from handshake
    while not local_received_requests.empty():
        await local_received_requests.get()

    # Send command
    cmd_seq = 123
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        seq=cmd_seq,
        payload=b'{"method":"get_status"}',
    )

    await local_channel.publish(msg)

    # Verify request
    request_bytes = await local_received_requests.get()
    assert local_received_requests.empty()

    # Decode request
    decoder = create_local_decoder(local_key=LOCAL_KEY, connect_nonce=TEST_CONNECT_NONCE, ack_nonce=TEST_ACK_NONCE)
    msgs = list(decoder(request_bytes))
    assert len(msgs) == 1
    assert msgs[0].protocol == RoborockMessageProtocol.RPC_REQUEST
    assert msgs[0].payload == b'{"method":"get_status"}'
