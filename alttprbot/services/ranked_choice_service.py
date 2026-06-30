"""Ranked-choice election service.

Owns ballot validation and persistence plus STV tabulation. Discord-side concerns
(voter-role checks, building/refreshing the election post) stay in the presentation
layer.
"""

from typing import List, Optional

import pyrankvote

from alttprbot import models
from alttprbot.repositories import RankedChoiceRepository


class RankedChoiceService:
    def __init__(self) -> None:
        self.repository = RankedChoiceRepository()

    async def get_election_with_candidates(
        self, election_id: int
    ) -> Optional[models.RankedChoiceElection]:
        return await self.repository.get_election_with_candidates(election_id)

    async def get_election_by_message_id(
        self, message_id: int
    ) -> Optional[models.RankedChoiceElection]:
        return await self.repository.get_election_by_message_id(message_id)

    async def create_election(self, **fields) -> models.RankedChoiceElection:
        return await self.repository.create_election(**fields)

    async def add_candidates(
        self, election: models.RankedChoiceElection, names: List[str]
    ) -> None:
        await self.repository.bulk_create_candidates(election, names)

    async def set_election_message_id(
        self, election: models.RankedChoiceElection, message_id: int
    ) -> None:
        await self.repository.set_message_id(election, message_id)

    async def close_election(self, election: models.RankedChoiceElection) -> None:
        await self.repository.close(election)

    async def get_user_votes(
        self, election: models.RankedChoiceElection, user_id: int
    ) -> List[models.RankedChoiceVotes]:
        return await self.repository.list_user_votes(election, user_id)

    async def submit_ballot(
        self, election: models.RankedChoiceElection, user_id: int, votes_data: list
    ) -> None:
        """Validate and persist a ballot. Raises ``ValueError`` on invalid input.

        ``election.candidates`` must already be fetched by the caller.
        """
        ranks = [vote["rank"] for vote in votes_data if vote.get("rank")]
        if len(ranks) != len(set(ranks)):
            raise ValueError("Each rank must be unique.")

        votes = []
        for vote in votes_data:
            if not vote.get("rank"):
                continue
            candidate = next(
                (c for c in election.candidates if c.id == vote["candidate_id"]), None
            )
            if not candidate:
                raise ValueError(f"Invalid candidate {vote['candidate_id']}")
            votes.append(
                models.RankedChoiceVotes(
                    election=election, candidate=candidate, user_id=user_id, rank=vote["rank"]
                )
            )

        votes.sort(key=lambda v: v.rank)
        await self.repository.bulk_create_votes(votes)

    async def calculate_results(self, election: models.RankedChoiceElection) -> None:
        """Tabulate the election via single transferable vote and persist the outcome.

        Marks the winning candidates and stores the human-readable result text on
        the election. Hydrates the candidates/votes itself, so the caller need not.
        """
        await self.repository.fetch_for_results(election)

        candidates = {
            candidate.name: pyrankvote.Candidate(candidate.name)
            for candidate in election.candidates
        }
        voters = list(set([a.user_id for a in election.votes]))
        ballots = []
        for voter in voters:
            votes: List[models.RankedChoiceVotes] = [
                v for v in election.votes if v.user_id == voter
            ]
            votes.sort(key=lambda x: x.rank)
            ballot = pyrankvote.Ballot([candidates[v.candidate.name] for v in votes])
            ballots.append(ballot)

        election_result = pyrankvote.single_transferable_vote(
            candidates=candidates.values(), ballots=ballots, number_of_seats=election.seats
        )

        winners = election_result.get_winners()
        for winner in winners:
            winner_candidate = next(
                (c for c in election.candidates if c.name == winner.name), None
            )
            if winner_candidate:
                await self.repository.mark_winner(winner_candidate)

        await self.repository.save_results(election, str(election_result))
