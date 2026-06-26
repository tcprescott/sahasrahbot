"""UserService unit tests: the three RaceTime account-linking branches."""

from unittest.mock import AsyncMock, MagicMock

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


async def test_authorization_service_maps_permission_to_bool():
    service = AuthorizationService()
    service.repository = AsyncMock()

    service.repository.get_permission.return_value = object()
    assert await service.is_racetime_cmd_authorized("k", "alttpr") is True

    service.repository.get_permission.return_value = None
    assert await service.is_racetime_cmd_authorized("k", "alttpr") is False
