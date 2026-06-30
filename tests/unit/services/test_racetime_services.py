"""Unit tests for the RaceTime-surface services (repositories mocked)."""

from unittest.mock import AsyncMock, sentinel

from alttprbot.services import RaceRoomService, SpoilerRaceService, TournamentResultsService


# --- SpoilerRaceService ---

async def test_spoiler_get_for_room_delegates():
    service = SpoilerRaceService()
    service.repository = AsyncMock()
    service.repository.get_by_srl_id.return_value = sentinel.race

    assert await service.get_for_room("room-1") is sentinel.race
    service.repository.get_by_srl_id.assert_awaited_once_with("room-1")


async def test_spoiler_schedule_returns_model():
    service = SpoilerRaceService()
    service.repository = AsyncMock()
    service.repository.upsert.return_value = (sentinel.race, True)

    result = await service.schedule(srl_id="room-1", spoiler_url="http://x", studytime=900)

    assert result is sentinel.race
    service.repository.upsert.assert_awaited_once_with(
        srl_id="room-1", spoiler_url="http://x", studytime=900
    )


async def test_spoiler_mark_started_passes_a_timestamp():
    service = SpoilerRaceService()
    service.repository = AsyncMock()

    await service.mark_started(sentinel.race)

    args, _ = service.repository.mark_started.await_args
    assert args[0] is sentinel.race
    assert args[1] is not None  # a datetime was supplied


async def test_spoiler_delete_delegates():
    service = SpoilerRaceService()
    service.repository = AsyncMock()
    await service.delete(sentinel.race)
    service.repository.delete_instance.assert_awaited_once_with(sentinel.race)


# --- RaceRoomService ---

async def test_set_and_clear_unlisted_delegate():
    service = RaceRoomService()
    service.repository = AsyncMock()

    await service.set_unlisted("room-1", "alttpr")
    service.repository.set_unlisted.assert_awaited_once_with("room-1", "alttpr")

    await service.clear_unlisted("room-1")
    service.repository.clear_unlisted.assert_awaited_once_with("room-1")


async def test_get_override_whitelist_delegates():
    service = RaceRoomService()
    service.repository = AsyncMock()
    service.repository.get_override_whitelist.return_value = sentinel.row

    assert await service.get_override_whitelist("rtid", "alttpr") is sentinel.row
    service.repository.get_override_whitelist.assert_awaited_once_with("rtid", "alttpr")


# --- TournamentResultsService ---

async def test_tournament_results_get_by_srl_id_delegates():
    service = TournamentResultsService()
    service.repository = AsyncMock()
    service.repository.get_by_srl_id.return_value = sentinel.tr

    assert await service.get_by_srl_id("room-1") is sentinel.tr
    service.repository.get_by_srl_id.assert_awaited_once_with("room-1")
