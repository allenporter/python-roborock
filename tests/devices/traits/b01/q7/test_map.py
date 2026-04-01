from roborock.data import Q7MapList, Q7MapListEntry
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder


async def test_q7_api_map_trait_refresh_populates_cached_values(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """Map trait follows refresh + cached-value access pattern."""
    fake_channel.response_queue.append(message_builder.build({"map_list": [{"id": 101, "cur": True}]}))

    assert q7_api.map.map_list == []
    assert q7_api.map.current_map_id is None

    await q7_api.map.refresh()

    assert len(fake_channel.published_messages) == 1
    assert q7_api.map.map_list[0].id == 101
    assert q7_api.map.map_list[0].cur is True
    assert q7_api.map.current_map_id == 101


def test_q7_map_list_current_map_id_prefers_marked_current():
    """Current-map resolution prefers the entry marked current."""
    map_list = Q7MapList(
        map_list=[
            Q7MapListEntry(id=111, cur=False),
            Q7MapListEntry(id=222, cur=True),
        ]
    )

    assert map_list.current_map_id == 222
