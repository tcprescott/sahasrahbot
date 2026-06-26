"""TournamentGamesService unit tests: the search field allowlist (mass-assignment guard)."""

from unittest.mock import AsyncMock

from alttprbot.services import TournamentGamesService


async def test_search_drops_unknown_filter_keys():
    service = TournamentGamesService()
    service.repository = AsyncMock()
    service.repository.search.return_value = []

    await service.search({
        "event": "alttprleague",
        "episode_id": "42",
        "submitted": "1",
        # injection / typo vectors that must NOT reach the ORM
        "id": "1 OR 1=1",
        "settings__contains": "x",
        "bogus": "y",
    })

    service.repository.search.assert_awaited_once_with(
        {"event": "alttprleague", "episode_id": "42", "submitted": "1"}
    )


async def test_search_passes_through_when_all_allowed():
    service = TournamentGamesService()
    service.repository = AsyncMock()
    service.repository.search.return_value = [{"episode_id": 1}]

    result = await service.search({"event": "x"})
    assert result == [{"episode_id": 1}]
    service.repository.search.assert_awaited_once_with({"event": "x"})
