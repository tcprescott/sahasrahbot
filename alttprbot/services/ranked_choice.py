"""Ranked-choice elections: showing a voter their ballot and recording it.

An election is open while ``active``. A ``private`` election only takes ballots from
members of its guild holding ``voter_role_id``. Each voter casts one ballot, which
can't be changed afterwards.
"""

import logging

from alttprbot import events, models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import bots
from alttprbot.util import discord_members, rankedchoice

logger = logging.getLogger(__name__)


async def _open_election(election_id: int) -> models.RankedChoiceElection:
    election = await models.RankedChoiceElection.get_or_none(id=election_id)
    if election is None or not election.active:
        raise NotFoundError("This election doesn't exist or has closed.")
    return election


async def _check_voter(election: models.RankedChoiceElection, user_id: int) -> None:
    if not election.private:
        return
    guild = await bots.discord().fetch_guild(election.guild_id)
    member = await discord_members.get_member(guild, user_id)
    if member is None:
        logger.warning("Voter %s isn't in guild %s for election %s", user_id, election.guild_id, election.id)
        raise PermissionDeniedError("We couldn't find you in the server this election belongs to.")
    if not any(role.id == election.voter_role_id for role in member.roles):
        raise PermissionDeniedError("You don't have the role this election needs to vote.")


async def get_ballot(election_id: int, user_id: int) -> dict:
    """The election and its candidates, plus the voter's ballot if they've already voted."""
    election = await _open_election(election_id)
    await _check_voter(election, user_id)
    candidates = await models.RankedChoiceCandidate.filter(election=election).order_by('id')
    votes = await models.RankedChoiceVotes.filter(election=election, user_id=user_id).order_by('rank')
    return {
        'id': election.id,
        'title': election.title,
        'description': election.description,
        'private': election.private,
        'seats': election.seats,
        'candidates': [{'id': c.id, 'name': c.name} for c in candidates],
        'ballot': [v.candidate_id for v in votes] if votes else None,
    }


async def cast_ballot(election_id: int, user_id: int, ranking: list[int]) -> dict:
    """Record a ballot. ``ranking`` is candidate ids, most preferred first; candidates
    left out aren't ranked."""
    election = await _open_election(election_id)
    await _check_voter(election, user_id)

    if await models.RankedChoiceVotes.filter(election=election, user_id=user_id).exists():
        raise PermissionDeniedError("You've already voted in this election. Ask its organiser if you need to change it.")
    if not ranking:
        raise InvalidInputError("Rank at least one candidate.")
    if len(set(ranking)) != len(ranking):
        raise InvalidInputError("Each candidate can only be ranked once.")

    candidates = {c.id: c for c in await models.RankedChoiceCandidate.filter(election=election)}
    unknown = [c for c in ranking if c not in candidates]
    if unknown:
        raise InvalidInputError("That ballot names a candidate who isn't in this election.")

    await models.RankedChoiceVotes.bulk_create([
        models.RankedChoiceVotes(election=election, candidate=candidates[cid], user_id=user_id, rank=rank)
        for rank, cid in enumerate(ranking, start=1)
    ])

    # alttprbot_discord/notifications.py refreshes the election's Discord post.
    events.publish(events.RankedChoiceBallotCast(election_id=election.id))

    return await get_ballot(election_id, user_id)


# --- running an election from Discord (alttprbot_discord/cogs/rankedchoice.py) ---


async def get_election(election_id: int):
    """The election, or None. Open or closed."""
    return await models.RankedChoiceElection.get_or_none(id=election_id)


async def create_election(*, title: str, description, candidates: list[str], seats: int, guild_id: int,
                          channel_id: int, owner_id: int, voter_role_id, show_vote_count: bool):
    """Open a new election with these candidates (names are stripped). It is private
    when ``voter_role_id`` is set. Returns it with ``candidates`` and ``votes`` fetched;
    its ``message_id`` is set afterwards with ``set_message_id``."""
    election = await models.RankedChoiceElection.create(
        title=title,
        description=description,
        private=voter_role_id is not None,
        active=True,
        guild_id=guild_id,
        channel_id=channel_id,
        message_id=None,  # set this later
        owner_id=owner_id,
        show_vote_count=show_vote_count,
        seats=seats,
        voter_role_id=voter_role_id,
    )
    await models.RankedChoiceCandidate.bulk_create(
        [models.RankedChoiceCandidate(election=election, name=candidate.strip()) for candidate in candidates])

    await election.fetch_related('candidates')
    await election.fetch_related('votes')
    return election


async def set_message_id(election_id: int, message_id: int) -> None:
    """Remember the Discord message that shows the election."""
    await models.RankedChoiceElection.filter(id=election_id).update(message_id=message_id)


async def end_election(message_id: int, user_id: int):
    """Close the election shown in ``message_id`` and count the ballots.

    Only its owner may. Raises ``DoesNotExist`` for a message that isn't an election,
    ``PermissionDeniedError`` for anyone else, and ``InvalidInputError`` when it has
    already closed. Returns the closed election, ready for ``refresh_election_post``.
    """
    election = await models.RankedChoiceElection.get(message_id=message_id)

    if election.owner_id != user_id:
        raise PermissionDeniedError("You are not the owner of this election.")
    if election.active is False:
        raise InvalidInputError("This election is already closed.")

    await election.fetch_related('candidates')
    await election.fetch_related('votes')

    await rankedchoice.calculate_results(election)

    election.active = False
    await election.save()
    return election
