"""AsyncTournamentService unit tests: race write orchestration (repo mocked)."""

import datetime
from unittest.mock import AsyncMock, sentinel

from alttprbot.services import AsyncTournamentService


async def test_submit_reattempt_delegates():
    service = AsyncTournamentService()
    service.repository = AsyncMock()
    await service.submit_reattempt(sentinel.race, "ran into a wall")
    service.repository.mark_reattempted.assert_awaited_once_with(sentinel.race, "ran into a wall")


async def test_claim_for_review_delegates():
    service = AsyncTournamentService()
    service.repository = AsyncMock()
    await service.claim_for_review(sentinel.race, sentinel.reviewer)
    service.repository.set_reviewer.assert_awaited_once_with(sentinel.race, sentinel.reviewer)


async def test_submit_review_injects_reviewed_at_and_delegates():
    service = AsyncTournamentService()
    service.repository = AsyncMock()

    await service.submit_review(
        sentinel.race, review_status="pass", reviewer_notes="ok", reviewer=sentinel.reviewer
    )

    service.repository.save_review.assert_awaited_once()
    _, kwargs = service.repository.save_review.await_args
    assert kwargs["review_status"] == "pass"
    assert kwargs["reviewer_notes"] == "ok"
    assert kwargs["reviewer"] is sentinel.reviewer
    assert isinstance(kwargs["reviewed_at"], datetime.datetime)
