"""RankedChoiceService happy-path integration test (live ORM)."""

from alttprbot import models
from alttprbot.services import RankedChoiceService


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
