"""Tests for the CleanRecordTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.clean_record import CleanRecordTrait
from roborock.roborock_typing import RoborockCommand
from tests.mock_data import CLEAN_RECORD

CLEAN_SUMMARY_DATA = [
    1442559,
    24258125000,
    296,
    [
        1738864366,
    ],
]

CLEAN_RECORD_DATA = [
    1738864366,
    1738868964,
    4358,
    81122500,
    0,
    0,
    1,
    1,
    21,
]


@pytest.fixture(autouse=True)
async def clean_summary_fixture(
    device: RoborockDevice,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Fixture to set up the clean summary for tests.

    The CleanRecordTrait depends on the CleanSummaryTrait, so we need to
    prepare that first.
    """
    assert device.v1_properties
    mock_rpc_channel.send_command.side_effect = [
        CLEAN_SUMMARY_DATA,
    ]
    await device.v1_properties.clean_summary.refresh()
    mock_rpc_channel.send_command.reset_mock()


@pytest.fixture
def clean_record_trait(device: RoborockDevice) -> CleanRecordTrait:
    """Create a CleanRecordTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.clean_record


async def test_get_clean_record_success(
    clean_record_trait: CleanRecordTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test successfully getting the last clean record."""
    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        CLEAN_RECORD_DATA,
    ]

    # Call the method
    await clean_record_trait.refresh()

    # Verify the result
    assert clean_record_trait.begin == 1738864366
    assert clean_record_trait.end == 1738868964
    assert clean_record_trait.duration == 4358
    assert clean_record_trait.area == 81122500
    assert clean_record_trait.complete is None
    assert clean_record_trait.start_type is None
    assert clean_record_trait.clean_type is None
    assert clean_record_trait.finish_reason is None

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_CLEAN_RECORD, params=[1738864366]),
        ]
    )


async def test_get_clean_record_dict_response(
    clean_record_trait: CleanRecordTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test successfully getting the last clean record as a dictionary."""
    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        CLEAN_RECORD,
    ]

    # Call the method
    await clean_record_trait.refresh()

    # Verify the result
    assert clean_record_trait.begin == 1672543330
    assert clean_record_trait.end == 1672544638
    assert clean_record_trait.duration == 1176
    assert clean_record_trait.area == 20965000
    assert clean_record_trait.complete == 1
    assert clean_record_trait.start_type == 2
    assert clean_record_trait.clean_type == 3
    assert clean_record_trait.finish_reason == 56
    assert clean_record_trait.dust_collection_status == 1
    assert clean_record_trait.avoid_count == 19
    assert clean_record_trait.wash_count == 2
    assert clean_record_trait.map_flag == 0

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_CLEAN_RECORD, params=[1738864366]),
        ]
    )
