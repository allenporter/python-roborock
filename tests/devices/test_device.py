"""Tests for the Device class."""

from unittest.mock import AsyncMock, Mock

from roborock.containers import HomeData, UserData
from roborock.devices.device import DeviceVersion, RoborockDevice

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
HOME_DATA = HomeData.from_dict(mock_data.HOME_DATA_RAW)


async def test_device_connection() -> None:
    """Test the Device connection setup."""

    unsub = Mock()
    subscribe = AsyncMock()
    subscribe.return_value = unsub
    mqtt_channel = AsyncMock()
    mqtt_channel.subscribe = subscribe

    device = RoborockDevice(
        USER_DATA,
        device_info=HOME_DATA.devices[0],
        product_info=HOME_DATA.products[0],
        mqtt_channel=mqtt_channel,
    )
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.device_version == DeviceVersion.V1

    assert not subscribe.called

    await device.connect()
    assert subscribe.called
    assert not unsub.called

    await device.close()
    assert unsub.called
