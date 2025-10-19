"""Tests for the DockSummaryTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.code_mappings import (
    RoborockDockDustCollectionModeCode,
    RoborockDockTypeCode,
    RoborockDockWashTowelModeCode,
)
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.dock_summary import DockSummaryTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

DUST_COLLECTION_DATA = {"mode": 4}
WASH_TOWEL_DATA = {"wash_mode": 2}
SMART_WASH_DATA = {"smart_wash": 5, "wash_interval": 6}


@pytest.fixture
def dock_summary_trait(device: RoborockDevice) -> DockSummaryTrait:
    """Create a DockSummaryTrait instance with mocked dependencies."""
    assert device.v1_properties
    assert device.v1_properties.dock_summary
    return device.v1_properties.dock_summary


@pytest.fixture
def status_trait(device: RoborockDevice) -> StatusTrait:
    """Create a StatusTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.status


@pytest.fixture(autouse=True)
async def discover_features_fixture(
    device: RoborockDevice,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode | None,
) -> None:
    """Fixture to set up the clean summary for tests.

    The CleanRecordTrait depends on the CleanSummaryTrait, so we need to
    prepare that first.
    """
    assert device.v1_properties
    mock_rpc_channel.send_command.side_effect = [
        [mock_data.APP_GET_INIT_STATUS],
        {
            **mock_data.STATUS,
            "dock_type": dock_type_code,
        },
    ]
    await device.v1_properties.discover_features()
    assert device.v1_properties.status.dock_type == dock_type_code
    mock_rpc_channel.send_command.reset_mock()


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s8_dock),
        (RoborockDockTypeCode.p10_dock),
        (RoborockDockTypeCode.qrevo_s_dock),
    ],
)
async def test_dock_summary_refresh(
    dock_summary_trait: DockSummaryTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test successfully refreshing the dock summary."""
    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        DUST_COLLECTION_DATA,
        WASH_TOWEL_DATA,
        SMART_WASH_DATA,
    ]

    # Call the method
    await dock_summary_trait.refresh()

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_DUST_COLLECTION_MODE),
            call(RoborockCommand.GET_WASH_TOWEL_MODE),
            call(RoborockCommand.GET_SMART_WASH_PARAMS),
        ]
    )

    # Verify the summary object contains the traits
    assert dock_summary_trait.dust_collection_mode
    assert dock_summary_trait.dust_collection_mode.mode == RoborockDockDustCollectionModeCode.max
    assert dock_summary_trait.wash_towel_mode
    assert dock_summary_trait.wash_towel_mode.wash_mode == RoborockDockWashTowelModeCode.deep
    assert dock_summary_trait.smart_wash_params
    assert dock_summary_trait.smart_wash_params.smart_wash == 5
    assert dock_summary_trait.smart_wash_params.wash_interval == 6


@pytest.mark.parametrize(
    ("dock_type_code"),
    [
        (RoborockDockTypeCode.s7_max_ultra_dock),  # Not in WASH_N_FILL_DOCK_TYPES
    ],
)
async def test_minimal_dock(
    dock_summary_trait: DockSummaryTrait,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test successfully refreshing the dock summary."""
    # Setup mock to return the sample clean summary and clean record
    mock_rpc_channel.send_command.side_effect = [
        DUST_COLLECTION_DATA,
    ]

    # Call the method
    await dock_summary_trait.refresh()

    # Verify the RPC calls were made correctly
    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_DUST_COLLECTION_MODE),
        ]
    )

    # Verify the summary object contains the traits
    assert dock_summary_trait.dust_collection_mode
    assert dock_summary_trait.dust_collection_mode.mode == RoborockDockDustCollectionModeCode.max
    assert dock_summary_trait.wash_towel_mode is None
    assert dock_summary_trait.smart_wash_params is None


@pytest.mark.parametrize(("dock_type_code"), [(RoborockDockTypeCode.no_dock)])
async def test_dock_summary_none_traits(
    device: RoborockDevice,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Test dock summary with optional traits as None."""
    assert device.v1_properties
    assert device.v1_properties.dock_summary is None
