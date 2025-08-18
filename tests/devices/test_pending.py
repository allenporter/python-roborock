"""Tests for the PendingRpcs class."""

import asyncio

import pytest

from roborock.devices.pending import PendingRpcs
from roborock.exceptions import RoborockException


@pytest.fixture(name="pending_rpcs")
def setup_pending_rpcs() -> PendingRpcs[int, str]:
    """Fixture to set up the PendingRpcs for tests."""
    return PendingRpcs[int, str]()


async def test_start_duplicate_rpc_raises_exception(pending_rpcs: PendingRpcs[int, str]) -> None:
    """Test that starting a duplicate RPC raises an exception."""
    key = 1
    await pending_rpcs.start(key)
    with pytest.raises(RoborockException, match=f"Request ID {key} already pending, cannot send command"):
        await pending_rpcs.start(key)


async def test_resolve_pending_rpc(pending_rpcs: PendingRpcs[int, str]) -> None:
    """Test resolving a pending RPC."""
    key = 1
    value = "test_result"
    future = await pending_rpcs.start(key)
    await pending_rpcs.resolve(key, value)
    result = await future
    assert result == value


async def test_resolve_unsolicited_message(
    pending_rpcs: PendingRpcs[int, str], caplog: pytest.LogCaptureFixture
) -> None:
    """Test resolving an unsolicited message does not raise."""
    key = 1
    value = "test_result"
    await pending_rpcs.resolve(key, value)


async def test_pop_pending_rpc(pending_rpcs: PendingRpcs[int, str]) -> None:
    """Test popping a pending RPC, which should cancel the future."""
    key = 1
    future = await pending_rpcs.start(key)
    await pending_rpcs.pop(key)
    with pytest.raises(asyncio.CancelledError):
        await future


async def test_pop_non_existent_rpc(pending_rpcs: PendingRpcs[int, str]) -> None:
    """Test that popping a non-existent RPC does not raise an exception."""
    key = 1
    await pending_rpcs.pop(key)


async def test_concurrent_rpcs(pending_rpcs: PendingRpcs[int, str]) -> None:
    """Test handling multiple concurrent RPCs."""

    async def start_and_resolve(key: int, value: str) -> str:
        future = await pending_rpcs.start(key)
        await asyncio.sleep(0.01)  # yield
        await pending_rpcs.resolve(key, value)
        return await future

    tasks = [
        asyncio.create_task(start_and_resolve(1, "result1")),
        asyncio.create_task(start_and_resolve(2, "result2")),
        asyncio.create_task(start_and_resolve(3, "result3")),
    ]

    results = await asyncio.gather(*tasks)
    assert results == ["result1", "result2", "result3"]
