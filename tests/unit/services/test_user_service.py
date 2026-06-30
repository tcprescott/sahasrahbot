"""UserService unit tests: the three RaceTime account-linking branches."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from tortoise.exceptions import IntegrityError

from alttprbot.services import AuthorizationService, UserService


async def test_link_upserts_by_discord_when_no_rtgg_user():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_by_rtgg_id.return_value = None
    service.repository.get_by_discord_id.return_value = MagicMock()  # discord user exists

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    service.repository.upsert_by_discord_id.assert_awaited_once_with(
        10, {"rtgg_id": "rt1", "rtgg_access_token": "tok", "display_name": "Alice"}
    )
    service.repository.merge.assert_not_awaited()


async def test_link_upserts_by_rtgg_when_no_conflict():
    service = UserService()
    service.repository = AsyncMock()
    same = MagicMock()
    service.repository.get_by_rtgg_id.return_value = same
    service.repository.get_by_discord_id.return_value = same  # same row -> no merge

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    service.repository.upsert_by_rtgg_id.assert_awaited_once_with(
        "rt1", {"discord_user_id": 10, "rtgg_access_token": "tok", "display_name": "Alice"}
    )
    service.repository.merge.assert_not_awaited()


async def test_link_merges_when_two_distinct_users_exist():
    service = UserService()
    service.repository = AsyncMock()
    rtgg_user = MagicMock()
    discord_user = MagicMock()
    service.repository.get_by_rtgg_id.return_value = rtgg_user
    service.repository.get_by_discord_id.return_value = discord_user
    kept = MagicMock()
    kept.save = AsyncMock()
    service.repository.merge.return_value = kept

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    service.repository.merge.assert_awaited_once_with(rtgg_user, discord_user)
    assert kept.display_name == "Alice"
    kept.save.assert_awaited_once()


async def test_unlink_racetime_account_clears_link():
    service = UserService()
    service.repository = AsyncMock()
    linked_user = MagicMock(rtgg_id="rt1")
    service.repository.get_by_discord_id.return_value = linked_user

    await service.unlink_racetime_account(10)

    service.repository.clear_racetime_link.assert_awaited_once_with(linked_user)


async def test_unlink_racetime_account_raises_when_no_user():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_by_discord_id.return_value = None

    with pytest.raises(ValueError):
        await service.unlink_racetime_account(10)

    service.repository.clear_racetime_link.assert_not_awaited()


async def test_unlink_racetime_account_raises_when_not_linked():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_by_discord_id.return_value = MagicMock(rtgg_id=None)

    with pytest.raises(ValueError):
        await service.unlink_racetime_account(10)

    service.repository.clear_racetime_link.assert_not_awaited()


async def test_update_display_name_rejects_empty():
    service = UserService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.update_display_name(MagicMock(), "   ")

    service.repository.set_display_name.assert_not_awaited()


async def test_update_display_name_rejects_too_long():
    service = UserService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.update_display_name(MagicMock(), "x" * 33)

    service.repository.set_display_name.assert_not_awaited()


async def test_update_display_name_strips_and_saves():
    service = UserService()
    service.repository = AsyncMock()
    user = MagicMock()

    await service.update_display_name(user, "  Alice  ")

    service.repository.set_display_name.assert_awaited_once_with(user, "Alice")


async def test_update_display_name_raises_on_duplicate():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.set_display_name.side_effect = IntegrityError()

    with pytest.raises(ValueError):
        await service.update_display_name(MagicMock(), "Alice")


async def test_authorization_service_maps_permission_to_bool():
    service = AuthorizationService()
    service.repository = AsyncMock()

    service.repository.get_permission.return_value = object()
    assert await service.is_racetime_cmd_authorized("k", "alttpr") is True

    service.repository.get_permission.return_value = None
    assert await service.is_racetime_cmd_authorized("k", "alttpr") is False
