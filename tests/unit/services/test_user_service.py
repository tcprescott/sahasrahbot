"""UserService unit tests: the three RaceTime account-linking branches."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from tortoise.exceptions import IntegrityError

from alttprbot.services import AuthorizationService, UserService


async def test_link_upserts_by_discord_when_no_rtgg_user():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_by_rtgg_id.return_value = None
    service.repository.get_by_discord_id.return_value = MagicMock(display_name=None)  # discord user exists, no name yet

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
    same = MagicMock(display_name=None)
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
    kept = MagicMock(display_name=None)
    kept.save = AsyncMock()
    service.repository.merge.return_value = kept

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    service.repository.merge.assert_awaited_once_with(rtgg_user, discord_user)
    assert kept.display_name == "Alice"
    kept.save.assert_awaited_once()


async def test_link_preserves_existing_display_name_on_discord_upsert():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_by_rtgg_id.return_value = None
    service.repository.get_by_discord_id.return_value = MagicMock(display_name="Zeldex")

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    service.repository.upsert_by_discord_id.assert_awaited_once_with(
        10, {"rtgg_id": "rt1", "rtgg_access_token": "tok"}
    )


async def test_link_preserves_existing_display_name_on_rtgg_upsert():
    service = UserService()
    service.repository = AsyncMock()
    same = MagicMock(display_name="Zeldex")
    service.repository.get_by_rtgg_id.return_value = same
    service.repository.get_by_discord_id.return_value = same

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    service.repository.upsert_by_rtgg_id.assert_awaited_once_with(
        "rt1", {"discord_user_id": 10, "rtgg_access_token": "tok"}
    )


async def test_link_preserves_existing_display_name_on_merge():
    service = UserService()
    service.repository = AsyncMock()
    rtgg_user = MagicMock()
    discord_user = MagicMock()
    service.repository.get_by_rtgg_id.return_value = rtgg_user
    service.repository.get_by_discord_id.return_value = discord_user
    kept = MagicMock(display_name="Zeldex")
    kept.save = AsyncMock()
    service.repository.merge.return_value = kept

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )

    assert kept.display_name == "Zeldex"
    kept.save.assert_not_awaited()


async def test_link_swallows_integrity_error_on_merge_fallback_name():
    service = UserService()
    service.repository = AsyncMock()
    rtgg_user = MagicMock()
    discord_user = MagicMock()
    service.repository.get_by_rtgg_id.return_value = rtgg_user
    service.repository.get_by_discord_id.return_value = discord_user
    kept = MagicMock(display_name=None)
    kept.save = AsyncMock(side_effect=IntegrityError())
    service.repository.merge.return_value = kept

    await service.link_racetime_account(
        discord_user_id=10, display_name="Alice", rtgg_id="rt1", access_token="tok"
    )  # must not raise -- a collision on the fallback name shouldn't fail the whole link

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


async def test_update_display_name_rejects_non_string():
    service = UserService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.update_display_name(MagicMock(), 123)

    service.repository.set_display_name.assert_not_awaited()


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


async def test_get_account_summary_with_no_user():
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_by_discord_id.return_value = None

    summary = await service.get_account_summary(10)

    assert summary == {
        "display_name": None,
        "racetime": {"linked": False, "id": None, "url": None},
        "twitch": {"linked": False, "name": None},
    }


async def test_get_account_summary_with_linked_user():
    service = UserService()
    service.repository = AsyncMock()
    user = MagicMock(display_name="Zeldex", rtgg_id="rt1", twitch_name="zeldex_tv")
    user.racetime_profile = "https://racetime.gg/user/rt1/"
    service.repository.get_by_discord_id.return_value = user

    summary = await service.get_account_summary(10)

    assert summary == {
        "display_name": "Zeldex",
        "racetime": {"linked": True, "id": "rt1", "url": "https://racetime.gg/user/rt1/"},
        "twitch": {"linked": True, "name": "zeldex_tv"},
    }


async def test_set_own_display_name_validates_before_touching_repository():
    service = UserService()
    service.repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.set_own_display_name(10, "   ")

    service.repository.get_or_create_by_discord_id.assert_not_awaited()


async def test_set_own_display_name_creates_and_saves():
    service = UserService()
    service.repository = AsyncMock()
    user = MagicMock(display_name=None)
    service.repository.get_or_create_by_discord_id.return_value = (user, True)

    async def fake_set_display_name(target, name):
        target.display_name = name
    service.repository.set_display_name.side_effect = fake_set_display_name

    result = await service.set_own_display_name(10, "  Alice  ")

    service.repository.set_display_name.assert_awaited_once_with(user, "Alice")
    assert result == "Alice"


async def test_authorization_service_maps_permission_to_bool():
    service = AuthorizationService()
    service.repository = AsyncMock()

    service.repository.get_permission.return_value = object()
    assert await service.is_racetime_cmd_authorized("k", "alttpr") is True

    service.repository.get_permission.return_value = None
    assert await service.is_racetime_cmd_authorized("k", "alttpr") is False
