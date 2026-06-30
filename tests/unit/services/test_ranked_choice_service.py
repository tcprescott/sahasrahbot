"""RankedChoiceService unit tests: ballot validation rules."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from alttprbot.services import RankedChoiceService


def _election(candidate_ids):
    return SimpleNamespace(candidates=[SimpleNamespace(id=c) for c in candidate_ids])


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
