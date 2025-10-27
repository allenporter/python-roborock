"""Tests for the RoutinesTrait."""

from unittest.mock import AsyncMock

import pytest

from roborock.data.containers import HomeDataScene
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.routines import RoutinesTrait


@pytest.fixture(name="routines_trait")
def routines_trait_fixture(device: RoborockDevice) -> RoutinesTrait:
    """Fixture for the routines trait."""
    assert device.v1_properties
    return device.v1_properties.routines


async def test_get_routines(routines_trait: RoutinesTrait, web_api_client: AsyncMock) -> None:
    """Test getting routines."""
    web_api_client.get_routines.return_value = [HomeDataScene(id=1, name="test_scene")]
    routines = await routines_trait.get_routines()
    assert len(routines) == 1
    assert routines[0].name == "test_scene"
    web_api_client.get_routines.assert_called_once()


async def test_execute_routine(routines_trait: RoutinesTrait, web_api_client: AsyncMock) -> None:
    """Test executing a routine."""
    await routines_trait.execute_routine(1)
    web_api_client.execute_routine.assert_called_once_with(1)
