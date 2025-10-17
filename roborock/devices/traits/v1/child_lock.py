from roborock.containers import ChildLockStatus
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

_STATUS_PARAM = "lock_status"


class ChildLockTrait(ChildLockStatus, common.V1TraitMixin):
    """Trait for controlling the child lock of a Roborock device."""

    command = RoborockCommand.GET_CHILD_LOCK_STATUS
    requires_feature = "is_set_child_supported"

    async def enable(self) -> None:
        """Enable the child lock."""
        await self.rpc_channel.send_command(RoborockCommand.SET_CHILD_LOCK_STATUS, params={_STATUS_PARAM: 1})

    async def disable(self) -> None:
        """Disable the child lock."""
        await self.rpc_channel.send_command(RoborockCommand.SET_CHILD_LOCK_STATUS, params={_STATUS_PARAM: 0})
