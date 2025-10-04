"""Module for Roborock V1 devices maps content trait commands.

This is used to get the actual image data for the maps stored on the device.
"""


from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

from .status import StatusTrait


class MapsContentTrait(common.V1TraitMixin):
    """Trait for managing the maps content of Roborock devices.

    This trait is used to get the actual image data for the maps stored on the device.
    """

    command = RoborockCommand.GET_MAP_V1

    def __init__(self, status_trait: StatusTrait) -> None:
        """Initialize the MapsTrait.

        We keep track of the StatusTrait to ensure we have the latest
        status information when dealing with maps.
        """
        super().__init__()
        self._status_trait = status_trait
        self._image_content: dict[int, bytes] = {}

    @property
    def current_map(self) -> int | None:
        """Returns the currently active map (map_flag), if available."""
        return self._status_trait.current_map

    async def refresh(self) -> Self:
        """Refresh the contents of this trait."""
        response = await self.rpc_channel.send_command(self.command)
