"""Create traits for V1 devices."""

from dataclasses import dataclass, field, fields

from roborock.containers import HomeDataProduct
from roborock.devices.traits import Trait
from roborock.devices.v1_rpc_channel import V1RpcChannel

from .properties import CleanSummaryTrait, DoNotDisturbTrait, SoundVolumeTrait, StatusTrait

__all__ = [
    "create",
    "PropertiesApi",
    "properties",
]


@dataclass
class PropertiesApi(Trait):
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

        # Create traits and set the RPC channel
        for item in fields(self):
            if (trait := getattr(self, item.name, None)) is None:
                trait = item.type()
                setattr(self, item.name, trait)
            trait._rpc_channel = rpc_channel


def create(product: HomeDataProduct, rpc_channel: V1RpcChannel) -> PropertiesApi:
    """Create traits for V1 devices."""
    return PropertiesApi(product, rpc_channel)
