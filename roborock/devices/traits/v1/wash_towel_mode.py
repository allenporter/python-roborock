"""Trait for wash towel mode."""

from roborock.containers import WashTowelMode
from roborock.device_features import WASH_N_FILL_DOCK_TYPES
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class WashTowelModeTrait(WashTowelMode, common.V1TraitMixin):
    """Trait for wash towel mode."""

    command = RoborockCommand.GET_WASH_TOWEL_MODE
    requires_dock_type = WASH_N_FILL_DOCK_TYPES
