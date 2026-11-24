"""Elections: running a vote from the website, voting, closing and counting.

An election is a ``draft`` until an admin posts it, ``open`` while it takes
ballots, and ``closed`` once it is counted. Admins are the server's Administrators
and the bot owner. Voters must be members of the election's server, and hold its
voter role when one is set. A voter can change their ballot until the election
closes; the latest one counts. Results are public once it closes.

The tables are still called ``ranked_choice_*``: elections from before the voting
methods were added are ranked (STV) elections.

Discord lookups go through ``discord_directory``; Discord output goes through
events (``alttprbot_discord/notifications.py``), except posting, whose message id
the election needs.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from tortoise.transactions import in_transaction

from alttprbot import events, models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import discord_directory, election_count
from alttprbot.services.election_count import METHODS, STV

logger = logging.getLogger(__name__)

DRAFT, OPEN, CLOSED = 'draft', 'open', 'closed'
STATUSES = (DRAFT, OPEN, CLOSED)

MAX_CANDIDATES = 100
MAX_TITLE = 200
MAX_DESCRIPTION = 2000
MAX_NAME = 200

METHOD_LABELS = {STV: 'Ranked (STV)', 'approval': 'Approval', 'plurality': 'Plurality'}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _status(election: models.RankedChoiceElection) -> str:
    # Rows written before the status column existed are open or closed by `active`.
    if election.status in STATUSES:
        return election.status
    return OPEN if election.active else CLOSED


# --- who may do what ---------------------------------------------------------


async def is_admin(guild_id: Optional[int], user_id: int) -> bool:
    directory = discord_directory.get()
    if await directory.is_owner(user_id):
        return True
    return guild_id is not None and await directory.is_admin(guild_id, user_id)


async def _require_admin(guild_id: Optional[int], user_id: int) -> None:
    if not await is_admin(guild_id, user_id):
        raise PermissionDeniedError("Only administrators of that server can manage its elections.")


async def _admin_election(election_id: int, user_id: int) -> models.RankedChoiceElection:
    election = await models.RankedChoiceElection.get_or_none(id=election_id)
    if election is None:
        raise NotFoundError("That election doesn't exist.")
    await _require_admin(election.guild_id, user_id)
    return election


async def _check_voter(election: models.RankedChoiceElection, user_id: int) -> None:
    role_ids = await discord_directory.get().member_role_ids(election.guild_id, user_id)
    if role_ids is None:
        logger.warning("Voter %s isn't in guild %s for election %s", user_id, election.guild_id, election.id)
        raise PermissionDeniedError("Only members of the server running this election can vote in it.")
    if election.voter_role_id and election.voter_role_id not in role_ids:
        raise PermissionDeniedError("You don't have the role this election needs to vote.")


async def can_manage_elections(user_id: int) -> bool:
    """Whether to show this user the Elections tab: they administer a server the bot is in."""
    directory = discord_directory.get()
    return await directory.is_owner(user_id) or bool(await directory.admin_guilds(user_id))


async def servers(user_id: int) -> list[dict]:
    """The servers ``user_id`` can run elections in."""
    return [{'id': g.id, 'name': g.name} for g in await discord_directory.get().admin_guilds(user_id)]


async def server_options(guild_id: int, user_id: int) -> dict:
    """The channels and roles the create form offers for a server."""
    await _require_admin(guild_id, user_id)
    directory = discord_directory.get()
    return {
        'channels': [{'id': c.id, 'name': c.name} for c in await directory.text_channels(guild_id)],
        'roles': [{'id': r.id, 'name': r.name} for r in await directory.roles(guild_id)],
    }


# --- reading elections -------------------------------------------------------


async def _candidates(election: models.RankedChoiceElection) -> list[models.RankedChoiceCandidate]:
    return await models.RankedChoiceCandidate.filter(election_id=election.id).order_by('position', 'id')


async def ballot_count(election_id: int) -> int:
    return len(await models.RankedChoiceVotes.filter(election_id=election_id).distinct().values_list('user_id', flat=True))


async def _summary(election: models.RankedChoiceElection, guild_names: Optional[dict] = None) -> dict:
    guild_name = (guild_names or {}).get(election.guild_id)
    if guild_name is None and election.guild_id is not None:
        guild_name = await discord_directory.get().guild_name(election.guild_id)
    return {
        'id': election.id,
        'title': election.title,
        'guild_id': election.guild_id,
        'guild_name': guild_name,
        'method': election.method,
        'seats': election.seats,
        'status': _status(election),
        'closes_at': election.closes_at,
        'closed_at': election.closed_at,
        'ballots': await ballot_count(election.id),
    }


async def list_elections(user_id: int) -> list[dict]:
    """Elections in the servers ``user_id`` administers, newest first. The bot owner
    sees every election."""
    directory = discord_directory.get()
    guilds = {g.id: g.name for g in await directory.admin_guilds(user_id)}
    query = models.RankedChoiceElection.all()
    if not await directory.is_owner(user_id):
        query = query.filter(guild_id__in=list(guilds))
    return [await _summary(e, guilds) for e in await query.order_by('-id')]


async def get_for_admin(election_id: int, user_id: int) -> dict:
    """Everything the edit form needs."""
    election = await _admin_election(election_id, user_id)
    summary = await _summary(election)
    return {
        **summary,
        'description': election.description,
        'channel_id': election.channel_id,
        'message_id': election.message_id,
        'voter_role_id': election.voter_role_id,
        'show_vote_count': election.show_vote_count,
        'candidates': [{'id': c.id, 'name': c.name} for c in await _candidates(election)],
        'locked': summary['ballots'] > 0 or summary['status'] == CLOSED,
    }


async def get_election(election_id: int) -> Optional[models.RankedChoiceElection]:
    """The election, or None. Any status."""
    return await models.RankedChoiceElection.get_or_none(id=election_id)


async def post_view(election_id: int) -> Optional[dict]:
    """What the Discord post shows, as plain data; None if there's no such election."""
    election = await get_election(election_id)
    if election is None:
        return None
    candidates = await _candidates(election)
    names = {c.id: c.name for c in candidates}
    winners = [names[w] for w in (election.tally or {}).get('winners', []) if w in names]
    if not winners and _status(election) == CLOSED:
        # Closed before counts were stored: the old winner flags.
        winners = [c.name for c in candidates if c.winner]
    return {
        'id': election.id,
        'title': election.title,
        'description': election.description,
        'method': election.method,
        'method_label': METHOD_LABELS.get(election.method, election.method),
        'seats': election.seats,
        'status': _status(election),
        'ballots': await ballot_count(election.id),
        'show_vote_count': election.show_vote_count,
        'voter_role_id': election.voter_role_id,
        'owner_id': election.owner_id,
        'closes_at': election.closes_at,
        'closed_at': election.closed_at,
        'channel_id': election.channel_id,
        'message_id': election.message_id,
        'winners': winners,
    }


# --- creating and editing ----------------------------------------------------


@dataclass
class ElectionInput:
    """What the create/edit form sends."""
    guild_id: int
    channel_id: int
    title: str
    candidates: list[str]
    method: str = STV
    seats: int = 1
    description: Optional[str] = None
    voter_role_id: Optional[int] = None
    closes_at: Optional[datetime] = None
    show_vote_count: bool = True


def _check_text(data: ElectionInput) -> None:
    title = (data.title or '').strip()
    if not title:
        raise InvalidInputError("Give the election a title.")
    if len(title) > MAX_TITLE:
        raise InvalidInputError(f"Keep the title to {MAX_TITLE} characters.")
    if data.description and len(data.description) > MAX_DESCRIPTION:
        raise InvalidInputError(f"Keep the description to {MAX_DESCRIPTION} characters.")
    if data.method not in METHODS:
        raise InvalidInputError("Pick a voting method: ranked, approval or plurality.")


def _clean_candidates(candidates: list[str], *, publishing: bool) -> list[str]:
    names = [n.strip() for n in candidates if n and n.strip()]
    if any(len(n) > MAX_NAME for n in names):
        raise InvalidInputError(f"Keep each candidate's name to {MAX_NAME} characters.")
    lowered = [n.casefold() for n in names]
    if len(set(lowered)) != len(lowered):
        raise InvalidInputError("Each candidate can only be listed once.")
    if len(names) > MAX_CANDIDATES:
        raise InvalidInputError(f"An election can have at most {MAX_CANDIDATES} candidates.")
    if publishing and len(names) < 2:
        raise InvalidInputError("Add at least two candidates.")
    return names


def _check_closing_time(closes_at: Optional[datetime], *, publishing: bool) -> None:
    if closes_at is None:
        return
    if closes_at.tzinfo is None:
        raise InvalidInputError("The closing time needs a time zone.")
    if publishing and closes_at <= _now():
        raise InvalidInputError("The closing time has already passed.")


def _validate(data: ElectionInput, *, publishing: bool) -> list[str]:
    """Check the form and return the cleaned candidate names. Drafts may be
    incomplete; posting needs everything."""
    _check_text(data)
    names = _clean_candidates(data.candidates, publishing=publishing)
    seats = data.seats if data.method == STV else 1
    if seats < 1 or (names and seats >= len(names) and publishing):
        raise InvalidInputError("There must be fewer winners than candidates.")
    data.seats = seats
    _check_closing_time(data.closes_at, publishing=publishing)
    return names


async def _check_targets(data: ElectionInput) -> None:
    directory = discord_directory.get()
    if data.channel_id not in {c.id for c in await directory.text_channels(data.guild_id)}:
        raise InvalidInputError("SahasrahBot can't post in that channel. Pick another, or give it access.")
    if data.voter_role_id and data.voter_role_id not in {r.id for r in await directory.roles(data.guild_id)}:
        raise InvalidInputError("That role isn't in this server.")


async def _replace_candidates(election: models.RankedChoiceElection, names: list[str]) -> None:
    await models.RankedChoiceCandidate.filter(election_id=election.id).delete()
    await models.RankedChoiceCandidate.bulk_create([
        models.RankedChoiceCandidate(election=election, name=name, position=i)
        for i, name in enumerate(names)
    ])


def _apply(election: models.RankedChoiceElection, data: ElectionInput) -> None:
    election.guild_id = data.guild_id
    election.channel_id = data.channel_id
    election.title = data.title.strip()
    election.description = (data.description or '').strip() or None
    election.method = data.method
    election.seats = data.seats
    election.voter_role_id = data.voter_role_id
    election.private = data.voter_role_id is not None
    election.closes_at = data.closes_at
    election.show_vote_count = data.show_vote_count


async def create_draft(user_id: int, data: ElectionInput) -> dict:
    """Save a new, unposted election."""
    await _require_admin(data.guild_id, user_id)
    names = _validate(data, publishing=False)
    await _check_targets(data)
    election = models.RankedChoiceElection(owner_id=user_id, status=DRAFT, active=False, message_id=None)
    _apply(election, data)
    async with in_transaction():
        await election.save()
        await _replace_candidates(election, names)
    return await get_for_admin(election.id, user_id)


async def update(election_id: int, user_id: int, data: ElectionInput) -> dict:
    """Edit an election. Once anyone has voted, its candidates, method and winners
    can't change, so existing ballots stay valid; nothing changes after it closes."""
    election = await _admin_election(election_id, user_id)
    status = _status(election)
    if status == CLOSED:
        raise InvalidInputError("This election has closed and can't be edited.")
    if data.guild_id != election.guild_id:
        await _require_admin(data.guild_id, user_id)
    if status == OPEN and data.guild_id != election.guild_id:
        raise InvalidInputError("A posted election can't move to another server.")
    if status == OPEN and data.channel_id != election.channel_id:
        raise InvalidInputError("A posted election can't move to another channel.")
    names = _validate(data, publishing=status == OPEN)
    await _check_targets(data)

    current = [c.name for c in await _candidates(election)]
    locked = await ballot_count(election.id) > 0
    if locked and (names != current or data.method != election.method or data.seats != election.seats):
        raise InvalidInputError("People have already voted, so the candidates, method and winners can't change.")

    _apply(election, data)
    async with in_transaction():
        await election.save()
        if names != current:
            await _replace_candidates(election, names)
    if status == OPEN:
        events.publish(events.ElectionUpdated(election_id=election.id))
    return await get_for_admin(election.id, user_id)


async def publish(election_id: int, user_id: int) -> dict:
    """Post a draft in its Discord channel and open it for voting."""
    election = await _admin_election(election_id, user_id)
    if _status(election) != DRAFT:
        raise InvalidInputError("This election has already been posted.")
    candidates = await _candidates(election)
    data = ElectionInput(guild_id=election.guild_id, channel_id=election.channel_id, title=election.title,
                         candidates=[c.name for c in candidates], method=election.method, seats=election.seats,
                         description=election.description, voter_role_id=election.voter_role_id,
                         closes_at=election.closes_at, show_vote_count=election.show_vote_count)
    _validate(data, publishing=True)
    await _check_targets(data)

    election.status = OPEN
    election.active = True
    await election.save()
    try:
        message_id = await discord_directory.get().post_election(election.id)
    except Exception:
        election.status = DRAFT
        election.active = False
        await election.save()
        raise
    election.message_id = message_id
    await election.save()
    return await get_for_admin(election.id, user_id)


async def set_message_id(election_id: int, message_id: int) -> None:
    """Remember the Discord message that shows the election."""
    await models.RankedChoiceElection.filter(id=election_id).update(message_id=message_id)


async def delete(election_id: int, user_id: int) -> None:
    """Delete an election with its candidates and ballots. Its Discord post goes too."""
    election = await _admin_election(election_id, user_id)
    channel_id, message_id = election.channel_id, election.message_id
    async with in_transaction():
        await models.RankedChoiceVotes.filter(election_id=election.id).delete()
        await models.RankedChoiceCandidate.filter(election_id=election.id).delete()
        await models.RankedChoiceAuthorizedVoters.filter(election_id=election.id).delete()
        await election.delete()
    events.publish(events.ElectionDeleted(election_id=election_id, channel_id=channel_id, message_id=message_id))


# --- voting ------------------------------------------------------------------


async def _open_election(election_id: int) -> models.RankedChoiceElection:
    election = await models.RankedChoiceElection.get_or_none(id=election_id)
    if election is None or _status(election) == DRAFT:
        raise NotFoundError("This election doesn't exist.")
    if _status(election) == CLOSED:
        raise NotFoundError("This election has closed.")
    return election


async def get_ballot(election_id: int, user_id: int) -> dict:
    """The election and its candidates, plus the voter's ballot if they've voted."""
    election = await _open_election(election_id)
    await _check_voter(election, user_id)
    candidates = await _candidates(election)
    votes = await models.RankedChoiceVotes.filter(election_id=election.id, user_id=user_id).order_by('rank', 'id')
    return {
        'id': election.id,
        'title': election.title,
        'description': election.description,
        'private': election.private,
        'method': election.method,
        'seats': election.seats,
        'closes_at': election.closes_at,
        'guild_name': await discord_directory.get().guild_name(election.guild_id),
        'candidates': [{'id': c.id, 'name': c.name} for c in candidates],
        'ballot': [v.candidate_id for v in votes] if votes else None,
        'voted_at': max(v.updated for v in votes) if votes else None,
    }


async def cast_ballot(election_id: int, user_id: int, choices: list[int]) -> dict:
    """Record or replace a ballot. ``choices`` is candidate ids: the ranking, most
    preferred first (STV); every approved candidate (approval); or the one pick
    (plurality)."""
    election = await _open_election(election_id)
    await _check_voter(election, user_id)

    if not choices:
        raise InvalidInputError("Pick at least one candidate.")
    if len(set(choices)) != len(choices):
        raise InvalidInputError("Each candidate can only be chosen once.")
    if election.method == 'plurality' and len(choices) != 1:
        raise InvalidInputError("Pick exactly one candidate.")
    candidates = {c.id: c for c in await _candidates(election)}
    if any(c not in candidates for c in choices):
        raise InvalidInputError("That ballot names a candidate who isn't in this election.")

    ranked = election.method != 'approval'
    async with in_transaction():
        await models.RankedChoiceVotes.filter(election_id=election.id, user_id=user_id).delete()
        await models.RankedChoiceVotes.bulk_create([
            models.RankedChoiceVotes(election=election, candidate=candidates[cid], user_id=user_id,
                                     rank=rank if ranked else None)
            for rank, cid in enumerate(choices, start=1)
        ])

    events.publish(events.ElectionBallotCast(election_id=election.id))
    return await get_ballot(election_id, user_id)


# --- closing and results -----------------------------------------------------


async def _ballots(election: models.RankedChoiceElection) -> list[list[int]]:
    by_user: dict[int, list] = {}
    for v in await models.RankedChoiceVotes.filter(election_id=election.id).order_by('user_id', 'rank', 'id'):
        by_user.setdefault(v.user_id, []).append(v.candidate_id)
    return list(by_user.values())


async def _count(election: models.RankedChoiceElection, candidates: list[models.RankedChoiceCandidate]) -> dict:
    return election_count.count(election.method, [c.id for c in candidates], await _ballots(election),
                                seats=election.seats, seed=election.id)


async def _close(election: models.RankedChoiceElection) -> models.RankedChoiceElection:
    candidates = await _candidates(election)
    tally = await _count(election, candidates)
    winners = set(tally['winners'])
    async with in_transaction():
        for c in candidates:
            c.winner = c.id in winners
            await c.save(update_fields=['winner'])
        election.tally = tally
        election.status = CLOSED
        election.active = False
        election.closed_at = _now()
        await election.save()
    events.publish(events.ElectionClosed(election_id=election.id))
    return election


async def close(election_id: int, user_id: int) -> dict:
    """End an open election now and count it."""
    election = await _admin_election(election_id, user_id)
    if _status(election) != OPEN:
        raise InvalidInputError("Only an open election can be closed.")
    await _close(election)
    return await get_for_admin(election.id, user_id)


async def close_from_message(message_id: int, user_id: int) -> models.RankedChoiceElection:
    """The End election button on the Discord post."""
    election = await models.RankedChoiceElection.get_or_none(message_id=message_id)
    if election is None:
        raise NotFoundError("This message isn't an election.")
    await _require_admin(election.guild_id, user_id)
    if _status(election) != OPEN:
        raise InvalidInputError("This election is already closed.")
    return await _close(election)


async def close_due() -> int:
    """Scheduled: close every open election whose closing time has passed."""
    due = await models.RankedChoiceElection.filter(status=OPEN, closes_at__lte=_now())
    for election in due:
        try:
            await _close(election)
        except Exception:
            logger.exception("Couldn't close election %s at its closing time", election.id)
    return len(due)


async def results(election_id: int) -> dict:
    """The count of a closed election, public. Elections closed before counts were
    stored are recounted once and saved."""
    election = await models.RankedChoiceElection.get_or_none(id=election_id)
    if election is None or _status(election) == DRAFT:
        raise NotFoundError("This election doesn't exist.")
    if _status(election) != CLOSED:
        raise PermissionDeniedError("Results are shown when voting closes.")
    candidates = await _candidates(election)
    if election.tally is None:
        election.tally = await _count(election, candidates)
        await election.save(update_fields=['tally'])
    return {
        'id': election.id,
        'title': election.title,
        'description': election.description,
        'method': election.method,
        'seats': election.seats,
        'closed_at': election.closed_at or election.updated,
        'guild_name': await discord_directory.get().guild_name(election.guild_id) if election.guild_id else None,
        'candidates': [{'id': c.id, 'name': c.name} for c in candidates],
        'tally': election.tally,
    }
