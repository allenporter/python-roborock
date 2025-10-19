"""Trait for dust collection mode."""

from roborock.containers import DustCollectionMode
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class DustCollectionModeTrait(DustCollectionMode, common.V1TraitMixin):
    """Trait for dust collection mode."""

    command = RoborockCommand.GET_DUST_COLLECTION_MODE
