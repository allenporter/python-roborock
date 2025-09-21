from typing import Self

from roborock.containers import CleanSummary
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand
from roborock.util import unpack_list


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
