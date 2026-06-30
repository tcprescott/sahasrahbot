"""DiscordServerService unit tests: validation + repository delegation (mocked)."""

import pytest
from unittest.mock import AsyncMock

from alttprbot.services import DiscordServerService


async def test_add_category_delegates_to_repository():
    service = DiscordServerService()
    service.repository = AsyncMock()

    await service.add_category(
        guild_id=1,
        channel_id=2,
        category_title="Racing",
        category_description="desc",
        order=3,
    )

    service.repository.create_category.assert_awaited_once_with(
        guild_id=1,
        channel_id=2,
        category_title="Racing",
        category_description="desc",
        order=3,
    )


async def test_add_category_rejects_blank_title():
    service = DiscordServerService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.add_category(guild_id=1, channel_id=2, category_title="   ")

    service.repository.create_category.assert_not_awaited()


async def test_update_category_rejects_blank_title():
    service = DiscordServerService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.update_category(5, category_title="", category_description=None)

    service.repository.update_category.assert_not_awaited()


async def test_add_server_rejects_blank_description():
    service = DiscordServerService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.add_server(invite_id="abc", category_id=1, server_description="")

    service.repository.create_server.assert_not_awaited()


async def test_add_server_delegates_to_repository():
    service = DiscordServerService()
    service.repository = AsyncMock()

    await service.add_server(invite_id="abc", category_id=7, server_description="My Server")

    service.repository.create_server.assert_awaited_once_with(
        invite_id="abc",
        category_id=7,
        server_description="My Server",
    )
