"""Traits for properties of Roborock devices using the V1 API."""

from dataclasses import dataclass, field
from typing import Self

from roborock.containers import CleanSummary, DnDTimer, HomeDataProduct, ModelStatus, S7MaxVStatus, Status
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand
from roborock.util import unpack_list

__all__ = [
    "StatusTrait",
    "DoNotDisturbTrait",
    "CleanSummaryTrait",
    "SoundVolumeTrait",
]


class StatusTrait(Status, common.V1TraitMixin):
    """Trait for managing the status of Roborock devices."""

    command = RoborockCommand.GET_STATUS

    def __init__(self, product_info: HomeDataProduct) -> None:
        """Initialize the StatusTrait."""
        self._product_info = product_info

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a CleanSummary."""
        status_type: type[Status] = ModelStatus.get(self._product_info.model, S7MaxVStatus)
        if isinstance(response, list):
            response = response[0]
        if isinstance(response, dict):
            return status_type.from_dict(response)
        raise ValueError(f"Unexpected status format: {response!r}")


class DoNotDisturbTrait(DnDTimer, common.V1TraitMixin):
    """Trait for managing Do Not Disturb (DND) settings on Roborock devices."""

    command = RoborockCommand.GET_DND_TIMER

    async def set_dnd_timer(self, dnd_timer: DnDTimer) -> None:
        """Set the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.SET_DND_TIMER, params=dnd_timer.as_dict())

    async def clear_dnd_timer(self) -> None:
        """Clear the Do Not Disturb (DND) timer settings of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CLOSE_DND_TIMER)


class CleanSummaryTrait(CleanSummary, common.V1TraitMixin):
    """Trait for managing the clean summary of Roborock devices."""

    command = RoborockCommand.GET_CLEAN_SUMMARY

    @classmethod
    def _parse_type_response(cls, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a CleanSummary."""
        if isinstance(response, dict):
            return CleanSummaryTrait.from_dict(response)  # type: ignore[return-value]
        elif isinstance(response, list):
            clean_time, clean_area, clean_count, records = unpack_list(response, 4)
            return CleanSummaryTrait(  # type: ignore[return-value]
                clean_time=clean_time,
                clean_area=clean_area,
                clean_count=clean_count,
                records=records,
            )
        elif isinstance(response, int):
            return CleanSummaryTrait(clean_time=response)  # type: ignore[return-value]
        raise ValueError(f"Unexpected clean summary format: {response!r}")


# TODO: This is currently the pattern for holding all the commands that hold a
# single value, but it still seems too verbose. Maybe we can generate these
# dynamically or somehow make them less code.


@dataclass
class SoundVolume(common.RoborockValueBase):
    """Dataclass for sound volume."""

    volume: int | None = field(default=None, metadata={"roborock_value": True})
    """Sound volume level (0-100)."""


class SoundVolumeTrait(SoundVolume, common.V1TraitMixin):
    """Trait for controlling the sound volume of a Roborock device."""

    command = RoborockCommand.GET_SOUND_VOLUME

    async def set_volume(self, volume: int) -> None:
        """Set the sound volume of the device."""
        await self.rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params=[volume])
