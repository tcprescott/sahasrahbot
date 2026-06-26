"""Unit tests for the async-tournament services backing the discord cog (repos mocked)."""

from unittest.mock import AsyncMock, sentinel

from alttprbot.services import (
    AsyncTournamentLiveRaceService,
    AsyncTournamentPermissionsService,
    AsyncTournamentService,
    UserService,
)


async def test_save_race_delegates():
    service = AsyncTournamentService()
    service.repository = AsyncMock()
    await service.save_race(sentinel.race)
    service.repository.save_race.assert_awaited_once_with(sentinel.race)


async def test_save_race_fields_delegates():
    service = AsyncTournamentService()
    service.repository = AsyncMock()
    await service.save_race_fields(sentinel.race, ["status", "start_time"])
    service.repository.save_race_fields.assert_awaited_once_with(sentinel.race, ["status", "start_time"])


async def test_create_race_passes_kwargs():
    service = AsyncTournamentService()
    service.repository = AsyncMock()
    await service.create_race(
        tournament=sentinel.t, user=sentinel.u, permalink=sentinel.p,
        thread_id=5, thread_open_time=sentinel.when,
    )
    service.repository.create_race.assert_awaited_once_with(
        tournament=sentinel.t, user=sentinel.u, permalink=sentinel.p,
        thread_id=5, thread_open_time=sentinel.when,
    )


async def test_permissions_service_delegates():
    service = AsyncTournamentPermissionsService()
    service.repository = AsyncMock()
    service.repository.get_permission.return_value = None
    assert await service.get_permission(sentinel.t, sentinel.u, "admin") is None
    service.repository.get_permission.assert_awaited_once_with(sentinel.t, sentinel.u, "admin")


async def test_live_race_service_delegates():
    service = AsyncTournamentLiveRaceService()
    service.repository = AsyncMock()
    service.repository.get_by_racetime_slug.return_value = sentinel.lr
    assert await service.get_by_racetime_slug("alttpr/x") is sentinel.lr


async def test_user_get_or_create_without_display_name():
    # regression: cog calls this with no display_name; the service must allow it
    service = UserService()
    service.repository = AsyncMock()
    service.repository.get_or_create_by_discord_id.return_value = (sentinel.user, True)
    result = await service.get_or_create_by_discord_id(123)
    assert result is sentinel.user
    service.repository.get_or_create_by_discord_id.assert_awaited_once_with(123, display_name=None)
