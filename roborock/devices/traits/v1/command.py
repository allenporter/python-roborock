from typing import Any

from roborock import RoborockCommand
from roborock.protocols.v1_protocol import ParamsType


class CommandTrait:
    """Trait for sending commands to Roborock devices."""

    def __post_init__(self) -> None:
        """Post-initialization to set up the RPC channel.

        This is called automatically after the dataclass is initialized by the
        device setup code.
        """
        self._rpc_channel = None

    async def send(self, command: RoborockCommand | str, params: ParamsType = None) -> Any:
        """Send a command to the device."""
        if not self._rpc_channel:
            raise ValueError("Device trait in invalid state")
        return await self._rpc_channel.send_command(command, params=params)
