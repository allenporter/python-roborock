"""Create traits for V1 devices."""

from dataclasses import dataclass, field, fields

from roborock.containers import HomeDataProduct
from roborock.devices.traits import Trait
from roborock.devices.v1_rpc_channel import V1RpcChannel

from .properties import CleanSummaryTrait, DoNotDisturbTrait, SoundVolumeTrait, StatusTrait

__all__ = [
    "create_v1_traits",
    "Properties",
    "properties",
]


@dataclass
class Properties(Trait):
    """Common properties for V1 devices.

    This class holds all the traits that are common across all V1 devices.
    """

    # All v1 devices have these traits
    status: StatusTrait
    dnd: DoNotDisturbTrait
    clean_summary: CleanSummaryTrait
    sound_volume: SoundVolumeTrait

    # In the future optional fields can be added below based on supported features

    def __init__(self, product: HomeDataProduct, rpc_channel: V1RpcChannel) -> None:
        """Initialize the V1TraitProps with None values."""
        self.status = StatusTrait(product)

        for item in fields(self):
            if (trait := getattr(self, item.name, None)) is None:
                trait = item.type()
                setattr(self, item.name, trait)
            trait._rpc_channel = rpc_channel


def create_v1_traits(product: HomeDataProduct, rpc_channel: V1RpcChannel) -> list[Trait]:
    """Create traits for V1 devices."""
    return [
        Properties(product, rpc_channel)
        # Add optional traits here as needed in the future
    ]
