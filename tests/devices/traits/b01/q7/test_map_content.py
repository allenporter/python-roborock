import json
from unittest.mock import patch

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from vacuum_map_parser_base.map_data import MapData

from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import ParsedMapData
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder


async def test_q7_map_content_refresh_populates_cached_values(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    fake_channel.response_queue.extend(
        [
            message_builder.build({"map_list": [{"id": 1772093512, "cur": True}]}),
            message_builder.build_map_response(b"raw-map-payload"),
        ]
    )

    # Ensure we have map metadata first
    await q7_api.map.refresh()

    dummy_map_data = MapData()
    parsed_map_data = ParsedMapData(
        image_content=b"pngbytes",
        map_data=dummy_map_data,
    )
    with (
        patch(
            "roborock.devices.rpc.b01_q7_channel.decode_map_payload",
            return_value=b"inflated-payload",
        ),
        patch(
            "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
            return_value=parsed_map_data,
        ) as parse,
    ):
        await q7_api.map_content.refresh()

    assert q7_api.map_content.image_content == b"pngbytes"
    assert q7_api.map_content.map_data is dummy_map_data
    assert q7_api.map_content.raw_api_response == b"inflated-payload"

    parse.assert_called_once_with(b"inflated-payload")

    assert len(fake_channel.published_messages) == 2
    first = fake_channel.published_messages[0]
    first_payload = json.loads(unpad(first.payload, AES.block_size))
    assert first_payload["dps"]["10000"]["method"] == "service.get_map_list"

    second = fake_channel.published_messages[1]
    second_payload = json.loads(unpad(second.payload, AES.block_size))
    assert second_payload["dps"]["10000"]["method"] == "service.upload_by_mapid"
    assert second_payload["dps"]["10000"]["params"] == {"map_id": 1772093512}


async def test_q7_map_content_refresh_falls_back_to_first_map(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """If no current map marker exists, first map in list is used."""
    fake_channel.response_queue.extend(
        [
            message_builder.build({"map_list": [{"id": 111}, {"id": 222, "cur": False}]}),
            message_builder.build_map_response(b"raw-map-payload"),
        ]
    )

    # Load current map
    await q7_api.map.refresh()

    dummy_map_data = MapData()
    with (
        patch(
            "roborock.devices.rpc.b01_q7_channel.decode_map_payload",
            return_value=b"inflated-payload",
        ),
        patch(
            "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
            return_value=type("X", (), {"image_content": b"pngbytes", "map_data": dummy_map_data})(),
        ),
    ):
        await q7_api.map_content.refresh()

    second = fake_channel.published_messages[1]
    second_payload = json.loads(unpad(second.payload, AES.block_size))
    assert second_payload["dps"]["10000"]["params"] == {"map_id": 111}


async def test_q7_map_content_refresh_errors_without_map_list(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """Refresh should fail clearly when map list is unusable."""
    fake_channel.response_queue.append(message_builder.build({"map_list": []}))

    with pytest.raises(RoborockException, match="Unable to determine current map ID"):
        await q7_api.map_content.refresh()
