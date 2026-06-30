"""Unit tests for the RaceTime-surface services (repositories mocked)."""

from unittest.mock import AsyncMock, Mock, sentinel

from alttprbot.services import RaceRoomService, SpoilerRaceService, TournamentResultsService
from alttprbot.services._notify import racetime_gateway


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


def _gateway_returning(status, monkeypatch):
    gw = AsyncMock()
    gw.get_race_status.return_value = status
    monkeypatch.setattr(racetime_gateway, "get", lambda: gw)
    return gw


async def test_handle_existing_room_no_row_proceeds(monkeypatch):
    service = TournamentResultsService()
    service.repository = AsyncMock()
    service.repository.get_by_episode_id.return_value = None
    gw = _gateway_returning("open", monkeypatch)

    assert await service.handle_existing_room_for_episode(42, "alttpr") is True
    gw.get_race_status.assert_not_awaited()  # no row -> never queries racetime
    service.repository.delete.assert_not_awaited()


async def test_handle_existing_room_live_refuses(monkeypatch):
    race = Mock(srl_id="room-42")
    service = TournamentResultsService()
    service.repository = AsyncMock()
    service.repository.get_by_episode_id.return_value = race
    gw = _gateway_returning("in_progress", monkeypatch)

    assert await service.handle_existing_room_for_episode(42, "alttpr") is False
    gw.get_race_status.assert_awaited_once_with("alttpr", "room-42")
    service.repository.delete.assert_not_awaited()  # live room left intact


async def test_handle_existing_room_cancelled_deletes_and_proceeds(monkeypatch):
    race = Mock(srl_id="room-42")
    service = TournamentResultsService()
    service.repository = AsyncMock()
    service.repository.get_by_episode_id.return_value = race
    _gateway_returning("cancelled", monkeypatch)

    assert await service.handle_existing_room_for_episode(42, "alttpr") is True
    service.repository.delete.assert_awaited_once_with(race)
