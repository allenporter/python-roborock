"""Tests for the FileCache class."""

import pathlib
import pickle
from unittest.mock import AsyncMock, patch

import pytest

from roborock.devices.cache import CacheData
from roborock.devices.file_cache import FileCache


@pytest.fixture(name="cache_file")
def cache_file_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    """Fixture to provide a temporary cache file path."""
    return tmp_path / "test_cache.bin"


async def test_get_from_non_existent_cache(cache_file: pathlib.Path) -> None:
    """Test getting data when the cache file does not exist."""
    cache = FileCache(cache_file)
    data = await cache.get()
    assert isinstance(data, CacheData)
    assert data == CacheData()


async def test_set_and_flush_and_get(cache_file: pathlib.Path) -> None:
    """Test setting, flushing, and then getting data from the cache."""
    cache = FileCache(cache_file)
    test_data = CacheData(home_data="test_home_data")  # type: ignore
    await cache.set(test_data)
    await cache.flush()

    assert cache_file.exists()

    # Create a new cache instance to ensure data is loaded from the file
    new_cache = FileCache(cache_file)
    loaded_data = await new_cache.get()
    assert loaded_data == test_data


async def test_get_caches_in_memory(cache_file: pathlib.Path) -> None:
    """Test that get caches the data in memory and avoids re-reading the file."""
    cache = FileCache(cache_file)
    initial_data = await cache.get()

    with patch("roborock.devices.file_cache.load_value", new_callable=AsyncMock) as mock_load_value:
        # This call should use the in-memory cache
        second_get_data = await cache.get()
        assert second_get_data is initial_data
        mock_load_value.assert_not_called()


async def test_invalid_cache_data(cache_file: pathlib.Path) -> None:
    """Test that a TypeError is raised for invalid cache data."""
    with open(cache_file, "wb") as f:
        pickle.dump("invalid_data", f)

    cache = FileCache(cache_file)
    with pytest.raises(TypeError):
        await cache.get()


async def test_flush_no_data(cache_file: pathlib.Path) -> None:
    """Test that flush does nothing if there is no data to write."""
    cache = FileCache(cache_file)
    await cache.flush()
    assert not cache_file.exists()
