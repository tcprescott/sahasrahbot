"""RankedChoiceService unit tests: ballot validation rules + post-refresh enqueue."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from alttprbot.services import RankedChoiceService
from alttprbot.services._notify import discord_gateway, queue


def _election(candidate_ids, message_id=None):
    return SimpleNamespace(
        id=1, message_id=message_id,
        candidates=[SimpleNamespace(id=c) for c in candidate_ids],
    )


class _FakeGateway:
    def __init__(self):
        self.refreshed = []

    async def refresh_ranked_choice_post(self, election_id):
        self.refreshed.append(election_id)


async def test_submit_ballot_rejects_duplicate_ranks():
    service = RankedChoiceService()
    service.repository = AsyncMock()
    election = _election([1, 2])

    with pytest.raises(ValueError, match="unique"):
        await service.submit_ballot(election, 7, [
            {"candidate_id": 1, "rank": 1},
            {"candidate_id": 2, "rank": 1},
        ])
    service.repository.bulk_create_votes.assert_not_awaited()


async def test_submit_ballot_rejects_invalid_candidate():
    service = RankedChoiceService()
    service.repository = AsyncMock()
    election = _election([1, 2])

    with pytest.raises(ValueError, match="Invalid candidate"):
        await service.submit_ballot(election, 7, [{"candidate_id": 99, "rank": 1}])
    service.repository.bulk_create_votes.assert_not_awaited()


# The happy path (real RankedChoiceVotes construction + bulk_create) is covered by
# tests/integration/services/test_ranked_choice_service.py, which needs a live ORM.


async def test_close_election_enqueues_refresh_when_gateway_registered(monkeypatch):
    fake = _FakeGateway()
    monkeypatch.setattr(discord_gateway, "_impl", fake)
    captured = []
    monkeypatch.setattr(queue, "enqueue", captured.append)

    service = RankedChoiceService()
    service.repository = AsyncMock()
    election = _election([1], message_id=999)

    await service.close_election(election)

    service.repository.close.assert_awaited_once_with(election)
    assert len(captured) == 1
    await captured[0]  # drive the enqueued coroutine as the queue worker would
    assert fake.refreshed == [election.id]


async def test_close_election_skips_refresh_without_gateway(monkeypatch):
    monkeypatch.setattr(discord_gateway, "_impl", None)
    captured = []
    monkeypatch.setattr(queue, "enqueue", captured.append)

    service = RankedChoiceService()
    service.repository = AsyncMock()

    await service.close_election(_election([1], message_id=999))

    assert captured == []  # no never-awaited coroutine leaked


async def test_close_election_skips_refresh_without_message_id(monkeypatch):
    monkeypatch.setattr(discord_gateway, "_impl", _FakeGateway())
    captured = []
    monkeypatch.setattr(queue, "enqueue", captured.append)

    service = RankedChoiceService()
    service.repository = AsyncMock()

    await service.close_election(_election([1], message_id=None))

    assert captured == []


# submit_ballot's refresh enqueue is asserted in the integration test (the happy
# path constructs real RankedChoiceVotes rows, which needs a live ORM).
