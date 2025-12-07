from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, call, patch

import pytest

from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol


@pytest.fixture(name="mock_channel")
def mock_channel_fixture() -> AsyncMock:
    return AsyncMock(spec=MqttChannel)


@pytest.fixture(name="mock_send")
def mock_send_fixture(mock_channel) -> Generator[AsyncMock, None, None]:
    with patch("roborock.devices.traits.a01.send_decoded_command") as mock_send:
        yield mock_send


async def test_dyad_api_query_values(mock_channel: AsyncMock, mock_send: AsyncMock):
    """Test that DyadApi currently returns raw values without conversion."""
    api = DyadApi(mock_channel)

    mock_send.return_value = {
        RoborockDyadDataProtocol.POWER: 1,
        RoborockDyadDataProtocol.STATUS: 6,
        RoborockDyadDataProtocol.WATER_LEVEL: 3,
        RoborockDyadDataProtocol.MESH_LEFT: 120,
        RoborockDyadDataProtocol.BRUSH_LEFT: 90,
        RoborockDyadDataProtocol.SILENT_MODE_START_TIME: 85,
        RoborockDyadDataProtocol.RECENT_RUN_TIME: "3,4,5",
        RoborockDyadDataProtocol.TOTAL_RUN_TIME: 123456,
    }
    result = await api.query_values(
        [
            RoborockDyadDataProtocol.POWER,
            RoborockDyadDataProtocol.STATUS,
            RoborockDyadDataProtocol.WATER_LEVEL,
            RoborockDyadDataProtocol.MESH_LEFT,
            RoborockDyadDataProtocol.BRUSH_LEFT,
            RoborockDyadDataProtocol.SILENT_MODE_START_TIME,
            RoborockDyadDataProtocol.RECENT_RUN_TIME,
            RoborockDyadDataProtocol.TOTAL_RUN_TIME,
        ]
    )
    assert result == {
        # Note: Bugs here, returning raw values
        RoborockDyadDataProtocol.POWER: 1,
        RoborockDyadDataProtocol.STATUS: 6,
        RoborockDyadDataProtocol.WATER_LEVEL: 3,
        RoborockDyadDataProtocol.MESH_LEFT: 120,
        RoborockDyadDataProtocol.BRUSH_LEFT: 90,
        RoborockDyadDataProtocol.SILENT_MODE_START_TIME: 85,
        RoborockDyadDataProtocol.RECENT_RUN_TIME: "3,4,5",
        RoborockDyadDataProtocol.TOTAL_RUN_TIME: 123456,
    }

    # Note: Bug here, this is the wrong encoding for the query
    assert mock_send.call_args_list == [
        call(
            mock_channel,
            {
                RoborockDyadDataProtocol.ID_QUERY: [209, 201, 207, 214, 215, 227, 229, 230],
            },
        ),
    ]


@pytest.mark.parametrize(
    ("query", "response", "expected_result"),
    [
        (
            [RoborockDyadDataProtocol.STATUS],
            {
                7: 1,
                RoborockDyadDataProtocol.STATUS: 3,
                9999: -3,
            },
            {
                # Note: Bug here, should return enum value
                RoborockDyadDataProtocol.STATUS: 3,
                # Note: Bug here, unknown value should not be returned
                7: 1,
                9999: -3,
            },
        ),
        (
            [RoborockDyadDataProtocol.SILENT_MODE_START_TIME],
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: "invalid",
            },
            {
                # Note: Bug here, invalid value should not be returned
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: "invalid",
            },
        ),
        (
            [RoborockDyadDataProtocol.SILENT_MODE_START_TIME],
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: 85,
                RoborockDyadDataProtocol.POWER: 2,
                9999: -3,
            },
            {
                # Note: Bug here, should return time value
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: 85,
                # Note: Bug here, additional values should not be returned
                RoborockDyadDataProtocol.POWER: 2,
                9999: -3,
            },
        ),
    ],
    ids=[
        "ignored-unknown-protocol",
        "invalid-value",
        "additional-returned-values",
    ],
)
async def test_dyad_invalid_response_value(
    mock_channel: AsyncMock,
    mock_send: AsyncMock,
    query: list[RoborockDyadDataProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockDyadDataProtocol, Any],
):
    """Test that DyadApi currently returns raw values without conversion."""
    api = DyadApi(mock_channel)

    mock_send.return_value = response
    result = await api.query_values(query)
    assert result == expected_result


async def test_zeo_api_query_values(mock_channel: AsyncMock, mock_send: AsyncMock):
    """Test that ZeoApi currently returns raw values without conversion."""
    api = ZeoApi(mock_channel)

    mock_send.return_value = {
        RoborockZeoProtocol.STATE: 1,
        RoborockZeoProtocol.MODE: 3,
        RoborockZeoProtocol.WASHING_LEFT: 4,
    }
    result = await api.query_values(
        [RoborockZeoProtocol.STATE, RoborockZeoProtocol.MODE, RoborockZeoProtocol.WASHING_LEFT]
    )
    assert result == {
        # Note: Bug here, should return enum values
        RoborockZeoProtocol.STATE: 1,
        RoborockZeoProtocol.MODE: 3,
        RoborockZeoProtocol.WASHING_LEFT: 4,
    }
    # Note: Bug here, this is the wrong encoding for the query
    assert mock_send.call_args_list == [
        call(
            mock_channel,
            {
                RoborockZeoProtocol.ID_QUERY: [203, 204, 218],
            },
        ),
    ]


@pytest.mark.parametrize(
    ("query", "response", "expected_result"),
    [
        (
            [RoborockZeoProtocol.STATE],
            {
                7: 1,
                RoborockZeoProtocol.STATE: 1,
                9999: -3,
            },
            {
                # Note: Bug here, should return enum value
                RoborockZeoProtocol.STATE: 1,
                # Note: Bug here, unknown value should not be returned
                7: 1,
                9999: -3,
            },
        ),
        (
            [RoborockZeoProtocol.WASHING_LEFT],
            {
                RoborockZeoProtocol.WASHING_LEFT: "invalid",
            },
            {
                # Note: Bug here, invalid value should not be returned
                RoborockZeoProtocol.WASHING_LEFT: "invalid",
            },
        ),
        (
            [RoborockZeoProtocol.STATE],
            {
                RoborockZeoProtocol.STATE: 1,
                RoborockZeoProtocol.WASHING_LEFT: 2,
                9999: -3,
            },
            {
                RoborockZeoProtocol.STATE: 1,
                # Note: Bug here, these values were not requested and should not be returned
                RoborockZeoProtocol.WASHING_LEFT: 2,
                9999: -3,
            },
        ),
    ],
    ids=[
        "ignored-unknown-protocol",
        "invalid-value",
        "additional-returned-values",
    ],
)
async def test_zeo_invalid_response_value(
    mock_channel: AsyncMock,
    mock_send: AsyncMock,
    query: list[RoborockZeoProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockZeoProtocol, Any],
):
    """Test that ZeoApi currently returns raw values without conversion."""
    api = ZeoApi(mock_channel)

    mock_send.return_value = response
    result = await api.query_values(query)
    assert result == expected_result
