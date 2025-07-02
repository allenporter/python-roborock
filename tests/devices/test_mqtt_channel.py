"""Tests for the MqttChannel class."""

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.containers import HomeData, UserData
from roborock.devices.mqtt_channel import MqttChannel
from roborock.mqtt.session import MqttParams

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
TEST_MQTT_PARAMS = MqttParams(
    host="localhost",
    port=1883,
    tls=False,
    username="username",
    password="password",
    timeout=10.0,
)


@pytest.fixture(autouse=True)
def setup_mqtt_session() -> Generator[None, None, None]:
    """Fixture to set up the MQTT session for the tests."""
    with patch("roborock.devices.device_manager.create_mqtt_session"):
        yield


async def home_home_data_no_devices() -> HomeData:
    """Mock home data API that returns no devices."""
    return HomeData(
        id=1,
        name="Test Home",
        devices=[],
        products=[],
    )


async def mock_home_data() -> HomeData:
    """Mock home data API that returns devices."""
    return HomeData.from_dict(mock_data.HOME_DATA_RAW)


async def test_mqtt_channel() -> None:
    """Test MQTT channel setup."""

    mock_session = AsyncMock()

    channel = MqttChannel(mock_session, duid="abc123", rriot=USER_DATA.rriot, mqtt_params=TEST_MQTT_PARAMS)

    unsub = Mock()
    mock_session.subscribe.return_value = unsub

    callback = Mock()
    result = await channel.subscribe(callback)

    assert mock_session.subscribe.called
    assert mock_session.subscribe.call_args[0][0] == "rr/m/o/user123/username/abc123"
    assert mock_session.subscribe.call_args[0][1] == callback

    assert result == unsub
