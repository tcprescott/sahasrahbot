"""Data access for ranked-choice elections and votes."""

from typing import List, Optional

from alttprbot import models


class RankedChoiceRepository:
    @staticmethod
    async def get_election(election_id: int) -> Optional[models.RankedChoiceElection]:
        return await models.RankedChoiceElection.get_or_none(id=election_id)

    @staticmethod
    async def get_election_with_candidates(
        election_id: int,
    ) -> Optional[models.RankedChoiceElection]:
        election = await models.RankedChoiceElection.get_or_none(id=election_id)
        if election is not None:
            await election.fetch_related("candidates")
        return election

    @staticmethod
    async def list_user_votes(
        election: models.RankedChoiceElection, user_id: int
    ) -> List[models.RankedChoiceVotes]:
        return await election.votes.filter(user_id=user_id)

    @staticmethod
    async def bulk_create_votes(votes: List[models.RankedChoiceVotes]) -> None:
        await models.RankedChoiceVotes.bulk_create(votes)
