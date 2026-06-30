"""GuildConfigService unit tests: cache behavior, delegation, channel resolution."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiocache
import pytest

from alttprbot.services import GuildConfigService


def _service():
    # isolated cache so tests don't share the process-wide GUILD_CONFIG_CACHE
    service = GuildConfigService(cache=aiocache.Cache(aiocache.SimpleMemoryCache))
    service.repository = AsyncMock()
    return service


async def test_get_reads_repository_then_serves_from_cache():
    service = _service()
    service.repository.get.return_value = SimpleNamespace(value="daily-race")

    assert await service.get(1, "DailyAnnouncerChannel") == "daily-race"
    # second call hits cache; repository is not queried again
    assert await service.get(1, "DailyAnnouncerChannel") == "daily-race"
    service.repository.get.assert_awaited_once_with(1, "DailyAnnouncerChannel")


async def test_get_returns_default_when_absent():
    service = _service()
    service.repository.get.return_value = None

    assert await service.get(1, "Missing", default="fallback") == "fallback"


async def test_set_upserts_and_invalidates_cache():
    service = _service()
    await service.cache.set("Key_1_config", "stale")

    await service.set(1, "Key", "new")

    service.repository.upsert.assert_awaited_once_with(1, "Key", "new")
    assert not await service.cache.exists("Key_1_config")


async def test_delete_removes_row_and_cache():
    service = _service()
    await service.cache.set("Key_1_config", "stale")

    await service.delete(1, "Key")

    service.repository.delete.assert_awaited_once_with(1, "Key")
    assert not await service.cache.exists("Key_1_config")


async def test_get_channel_ids_parses_ids_and_resolves_names():
    service = _service()
    service.repository.get.return_value = SimpleNamespace(value="123, daily-race , ,456")

    def resolver(name):
        return 999 if name == "daily-race" else None

    result = await service.get_channel_ids(1, "DailyAnnouncerChannel", resolver=resolver)
    assert result == [123, 999, 456]


async def test_get_channel_ids_empty_when_unset():
    service = _service()
    service.repository.get.return_value = None
    result = await service.get_channel_ids(1, "DailyAnnouncerChannel", resolver=lambda n: None)
    assert result == []


async def test_get_all_guilds_with_parameter_delegates():
    service = _service()
    service.repository.list_for_parameter.return_value = [{"guild_id": 1}]
    assert await service.get_all_guilds_with_parameter("X") == [{"guild_id": 1}]
    service.repository.list_for_parameter.assert_awaited_once_with("X")
