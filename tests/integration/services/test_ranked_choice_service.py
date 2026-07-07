"""RankedChoiceService happy-path integration test (live ORM)."""

from alttprbot import models
from alttprbot.services import RankedChoiceService
from alttprbot.services._notify import discord_gateway, queue


class _FakeGateway:
    def __init__(self):
        self.refreshed = []

    async def refresh_ranked_choice_post(self, election_id):
        self.refreshed.append(election_id)


async def test_submit_ballot_persists_sorted_votes(tortoise_db):
    election = await models.RankedChoiceElection.create(owner_id=1, title="Test")
    c1 = await models.RankedChoiceCandidate.create(election=election, name="A")
    c2 = await models.RankedChoiceCandidate.create(election=election, name="B")
    await election.fetch_related("candidates")

    service = RankedChoiceService()
    await service.submit_ballot(election, user_id=7, votes_data=[
        {"candidate_id": c2.id, "rank": 2},
        {"candidate_id": c1.id, "rank": 1},
        {"candidate_id": c1.id, "rank": None},  # skipped (no rank)
    ])

    stored = await service.get_user_votes(election, 7)
    by_rank = sorted(stored, key=lambda v: v.rank)
    assert [v.rank for v in by_rank] == [1, 2]
    assert by_rank[0].candidate_id == c1.id
    assert by_rank[1].candidate_id == c2.id


async def test_submit_ballot_enqueues_post_refresh(tortoise_db, monkeypatch):
    fake = _FakeGateway()
    monkeypatch.setattr(discord_gateway, "_impl", fake)
    captured = []
    monkeypatch.setattr(queue, "enqueue", captured.append)

    election = await models.RankedChoiceElection.create(owner_id=1, title="Test", message_id=999)
    c1 = await models.RankedChoiceCandidate.create(election=election, name="A")
    await election.fetch_related("candidates")

    service = RankedChoiceService()
    await service.submit_ballot(election, user_id=7, votes_data=[
        {"candidate_id": c1.id, "rank": 1},
    ])

    assert len(captured) == 1
    await captured[0]  # drive the enqueued coroutine as the queue worker would
    assert fake.refreshed == [election.id]
