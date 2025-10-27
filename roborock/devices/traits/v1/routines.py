"""Routines trait for V1 devices."""

from roborock.data.containers import HomeDataScene
from roborock.web_api import UserWebApiClient


class RoutinesTrait:
    """Trait for interacting with routines."""

    def __init__(self, device_id: str, web_api: UserWebApiClient) -> None:
        """Initialize the routines trait."""
        self._device_id = device_id
        self._web_api = web_api

    async def get_routines(self) -> list[HomeDataScene]:
        """Get available routines."""
        return await self._web_api.get_routines(self._device_id)

    async def execute_routine(self, routine_id: int) -> None:
        """Execute a routine by its ID.

        Technically, routines are per-device, but the API does not
        require the device ID to execute them. This can execute a
        routine for any device but it is exposed here for convenience.
        """
        await self._web_api.execute_routine(routine_id)
