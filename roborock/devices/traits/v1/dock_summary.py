"""Trait for the dock summary."""

import asyncio
import logging
from typing import Self

from roborock.roborock_typing import DockSummary

from . import common
from .dust_collection_mode import DustCollectionModeTrait
from .smart_wash_params import SmartWashParamsTrait
from .wash_towel_mode import WashTowelModeTrait

_LOGGER = logging.getLogger(__name__)


class DockSummaryTrait(DockSummary, common.V1TraitMixin):
    """Trait for the dock summary."""

    def __init__(
        self,
        dust_collection_mode_trait: DustCollectionModeTrait,
        wash_towel_mode_trait: WashTowelModeTrait | None,
        smart_wash_params_trait: SmartWashParamsTrait | None,
    ) -> None:
        """Initialize the dock summary trait."""
        super().__init__()
        self._dust_collection_mode = dust_collection_mode_trait
        self._wash_towel_mode = wash_towel_mode_trait
        self._smart_wash_params = smart_wash_params_trait

    async def refresh(self) -> Self:
        """Refresh the dock summary."""
        tasks: list[asyncio.Task] = [asyncio.create_task(self._dust_collection_mode.refresh())]
        if self._wash_towel_mode is not None:
            tasks.append(asyncio.create_task(self._wash_towel_mode.refresh()))
        if self._smart_wash_params is not None:
            tasks.append(asyncio.create_task(self._smart_wash_params.refresh()))
        _LOGGER.debug("Waiting for %d Dock Summary task(s) to complete ", len(tasks))
        await asyncio.gather(*tasks)
        summary = DockSummary(self._dust_collection_mode, self._wash_towel_mode, self._smart_wash_params)
        self._update_trait_values(summary)
        return self
