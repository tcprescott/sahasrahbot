"""Async tournament rules, shared by the Discord cog and the website.

The ``/async`` cog (``alttprbot_discord/cogs/asynctournament.py``) and the web
routes (``alttprbot_api/blueprints/asynctournament.py``) both call this module, so
a rule lives in one place and every state change writes its own
``AsyncTournamentAuditLog`` entry, whichever front end made it.

Functions raise ``AsyncTournamentError`` when a rule says no. Its message is meant
for the player or moderator, and ``status`` is the HTTP status the website should
answer with. Callers turn it into an ephemeral Discord reply or an ``abort()``.

Scoring and the leaderboard stay in ``alttprbot/util/asynctournament.py``.
"""

import datetime
import logging
from collections import Counter
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional, Sequence, Tuple

import config
from alttprbot import models
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import asynctournament as scoring

# How long a player has to press Ready after their thread opens.
PENDING_GRACE_PERIOD = datetime.timedelta(minutes=20)
# How long before that deadline the thread gets a warning.
TIMEOUT_WARNING_LEAD = datetime.timedelta(minutes=10)
# An in-progress run is forfeited after this long.
IN_PROGRESS_LIMIT = datetime.timedelta(hours=12)
# Discord accounts must be this much older than the tournament, unless whitelisted.
MIN_ACCOUNT_AGE = datetime.timedelta(days=7)
# The website allows one reattempt per player per tournament.
MAX_REATTEMPTS = 1

ACTIVE_STATUSES = ("pending", "in_progress")


class AsyncTournamentError(SahasrahBotException):
    """A rule refused the action. ``str(error)`` is the message to show the user."""

    def __init__(self, message: str, status: int = 403):
        super().__init__(message)
        self.message = message
        self.status = status


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


# --- Discord gateway ---------------------------------------------------------
#
# Role-based permissions need a guild member's role IDs. Fetching them is Discord
# work, so the Discord side registers a lookup at startup (see sahasrahbot.py)
# instead of this module importing the bot.

MemberRoleLookup = Callable[[int, int], Awaitable[Optional[Sequence[int]]]]
_member_role_lookup: Optional[MemberRoleLookup] = None


def set_member_role_lookup(lookup: Optional[MemberRoleLookup]) -> None:
    """Register ``lookup(guild_id, discord_user_id) -> role IDs, or None if not a member``."""
    global _member_role_lookup
    _member_role_lookup = lookup


async def _member_role_ids(guild_id: int, discord_user_id: int) -> Optional[Sequence[int]]:
    if _member_role_lookup is None:
        logging.warning("No member role lookup registered; async tournament role permissions are unavailable.")
        return None
    return await _member_role_lookup(guild_id, discord_user_id)


# --- Permissions and audit log -----------------------------------------------

async def is_async_tournament_user(user: Optional[models.Users], tournament: models.AsyncTournament,
                                   roles: List[str]) -> bool:
    """True if ``user`` holds one of ``roles`` for ``tournament``, directly or through a Discord role.

    ``'public'`` in ``roles`` lets anyone in once the tournament is closed.
    """
    if 'public' in roles and not tournament.active:
        return True

    if user is None:
        return False

    if await tournament.permissions.filter(user=user, role__in=roles):
        return True

    if user.discord_user_id is None:
        return False

    role_ids = await _member_role_ids(tournament.guild_id, user.discord_user_id)
    if not role_ids:
        return False

    return bool(await tournament.permissions.filter(discord_role_id__in=list(role_ids), role__in=roles))


async def audit(tournament_id: int, action: str, details: str,
                user: Optional[models.Users] = None) -> models.AsyncTournamentAuditLog:
    return await models.AsyncTournamentAuditLog.create(
        tournament_id=tournament_id,
        user=user,
        action=action,
        details=details,
    )


async def get_user(discord_user_id: int) -> models.Users:
    user, _ = await models.Users.get_or_create(discord_user_id=discord_user_id)
    return user


def _require_runner(race: models.AsyncTournamentRace, discord_user_id: int, message: str) -> None:
    """``race.user`` must be fetched."""
    if race.user.discord_user_id != discord_user_id:
        raise AsyncTournamentError(message)


# --- Starting a run ------------------------------------------------------------

def count_runs_per_pool(races: Sequence[models.AsyncTournamentRace]) -> Counter:
    """Runs that count toward each pool's limit, by pool ID. Reattempted runs don't count.

    Each race's ``permalink`` must be fetched.
    """
    return Counter(r.permalink.pool_id for r in races if not r.reattempted)


async def get_pools_with_runs_left(tournament: models.AsyncTournament,
                                   user: models.Users) -> List[models.AsyncTournamentPermalinkPool]:
    await tournament.fetch_related('permalink_pools')
    history = await models.AsyncTournamentRace.filter(user=user, tournament=tournament).prefetch_related('permalink')
    counts = count_runs_per_pool(history)
    return [p for p in tournament.permalink_pools if counts[p.id] < tournament.runs_per_pool]


def _require_active(tournament: Optional[models.AsyncTournament]) -> models.AsyncTournament:
    if tournament is None:
        raise AsyncTournamentError("This channel is not configured for async tournaments.", 404)
    if tournament.active is False:
        raise AsyncTournamentError("This tournament is not currently active.")
    return tournament


async def check_can_start(tournament: Optional[models.AsyncTournament], discord_user_id: int,
                          account_created_at: datetime.datetime
                          ) -> Tuple[models.Users, List[models.AsyncTournamentPermalinkPool]]:
    """Whether a player may start a new run. Returns the player and the pools they can still play."""
    tournament = _require_active(tournament)

    if account_created_at > (tournament.created - MIN_ACCOUNT_AGE):
        await tournament.fetch_related('whitelist', 'whitelist__user')
        if discord_user_id not in [w.user.discord_user_id for w in tournament.whitelist]:
            raise AsyncTournamentError(
                "Your Discord account is too new to participate in this tournament.  Please contact a tournament "
                "administrator for manual verification and whitelisting.")

    user = await get_user(discord_user_id)
    if user.rtgg_id is None:
        raise AsyncTournamentError(
            "You must link your RaceTime.gg account to SahasrahBot before you can participate in an async "
            f"tournament.\n\nPlease visit <{config.APP_URL}/racetime/verification/initiate> to link your "
            "RaceTime account.")

    pools = await get_pools_with_runs_left(tournament, user)
    if not pools:
        raise AsyncTournamentError("You have already played all available pools for this tournament.")

    return user, pools


async def check_new_race(tournament: Optional[models.AsyncTournament], discord_user_id: int,
                         pool_name: Optional[str]) -> Tuple[models.Users, models.AsyncTournamentPermalinkPool]:
    """Re-check the rules when the player confirms, before their thread is created."""
    tournament = _require_active(tournament)

    if pool_name is None:
        raise AsyncTournamentError("Please choose a pool.", 400)

    user = await get_user(discord_user_id)

    if await tournament.races.filter(user=user, status__in=ACTIVE_STATUSES):
        raise AsyncTournamentError(
            "You already have an active race.  If you believe this is in error, please contact a moderator.")

    pool = await tournament.permalink_pools.filter(name=pool_name).first()  # TODO: add a unique constraint on this
    if pool is None:
        raise AsyncTournamentError("That pool does not exist in this tournament.", 404)

    if pool.id not in [p.id for p in await get_pools_with_runs_left(tournament, user)]:
        raise AsyncTournamentError("You have already played the maximum number of seeds from this pool.")

    return user, pool


async def start_race(tournament: models.AsyncTournament, user: models.Users,
                     pool: models.AsyncTournamentPermalinkPool, thread_id: int
                     ) -> Tuple[models.AsyncTournamentRace, models.AsyncTournamentPermalink]:
    """Pick a seed and record the new run. Call ``check_new_race`` first."""
    permalink = await scoring.get_eligible_permalink_from_pool(pool, user)

    await audit(tournament.id, "create_thread",
                f"Created thread {thread_id} for pool {pool.name}, permalink {permalink.url}", user)

    race = await models.AsyncTournamentRace.create(
        tournament=tournament,
        thread_id=thread_id,
        user=user,
        thread_open_time=utcnow(),
        permalink=permalink,
    )
    return race, permalink


# --- Running a run -------------------------------------------------------------

async def mark_ready(race: models.AsyncTournamentRace, discord_user_id: int) -> models.Users:
    """Move a pending run to in progress, before the countdown. ``race.user`` must be fetched."""
    _require_runner(race, discord_user_id, "Only the runner of this race can start it.")
    if race.status != "pending":
        raise AsyncTournamentError("This race must be in the pending state to start it.")

    user = await get_user(discord_user_id)
    await audit(race.tournament_id, "race_ready", f"{race.id} is marked as ready", user)

    race.status = "in_progress"
    await race.save()

    await audit(race.tournament_id, "race_countdown", f"{race.id} is starting a countdown", user)
    return user


async def record_start(race: models.AsyncTournamentRace, user: models.Users) -> None:
    """Start the clock, after the countdown."""
    race.start_time = utcnow()
    await race.save()
    await audit(race.tournament_id, "race_started", f"{race.id} has started", user)


def check_can_forfeit(race: models.AsyncTournamentRace, discord_user_id: int) -> None:
    """``race.user`` must be fetched."""
    _require_runner(race, discord_user_id, "Only the runner may forfeit this race.")
    if race.status not in ACTIVE_STATUSES:
        raise AsyncTournamentError("The race must be pending or in progress to forfeit it.")


async def forfeit(race: models.AsyncTournamentRace, discord_user_id: int) -> None:
    check_can_forfeit(race, discord_user_id)
    user = await get_user(discord_user_id)
    await audit(race.tournament_id, "runner_forfeit", f"{race.id} was forfeited by runner", user)
    race.status = "forfeit"
    await race.save()


async def finish(race: models.AsyncTournamentRace, discord_user_id: int) -> None:
    """``race.user`` must be fetched."""
    _require_runner(race, discord_user_id, "Only the player of this race may finish it.")
    if race.status != "in_progress":
        raise AsyncTournamentError("You may only finish a race that's in progress.")

    user = await get_user(discord_user_id)
    await audit(race.tournament_id, "race_finish", f"{race.id} has finished", user)
    race.end_time = utcnow()
    race.status = "finished"
    await race.save()


def check_can_submit(race: models.AsyncTournamentRace, discord_user_id: int) -> None:
    """``race.user`` must be fetched."""
    _require_runner(race, discord_user_id, "Only the player may submit a VoD.")


async def submit_vod(race: models.AsyncTournamentRace, discord_user_id: int, vod_url: str,
                     notes: Optional[str]) -> None:
    """``race.user`` must be fetched."""
    check_can_submit(race, discord_user_id)
    race.runner_vod_url = vod_url
    race.runner_notes = notes
    await race.save()
    await audit(race.tournament_id, "submit_vod", f"{race.id} VoD submitted: {vod_url}",
                await get_user(discord_user_id))


async def submit_igt(race: models.AsyncTournamentRace, discord_user_id: int, collection_rate: str,
                     igt: str) -> None:
    """``race.user`` must be fetched."""
    check_can_submit(race, discord_user_id)
    race.run_collection_rate = collection_rate
    race.run_igt = igt
    await race.save()
    await audit(race.tournament_id, "submit_igt", f"{race.id} collection rate {collection_rate}, IGT {igt}",
                await get_user(discord_user_id))


# --- Timeouts --------------------------------------------------------------------

async def extend_timeout(race: models.AsyncTournamentRace, discord_user_id: int,
                         minutes: int) -> datetime.datetime:
    """A moderator gives a pending run more time to start. Returns the new deadline."""
    if race.status != "pending":
        raise AsyncTournamentError("This race is not pending.  It cannot be extended.")

    await race.fetch_related("tournament")
    user = await get_user(discord_user_id)
    if not await is_async_tournament_user(user, race.tournament, ['admin', 'mod']):
        raise AsyncTournamentError("You are not authorized to extend the timeout for this tournament race.")

    current = race.thread_timeout_time or (race.thread_open_time + PENDING_GRACE_PERIOD)
    race.thread_timeout_time = current + datetime.timedelta(minutes=minutes)
    await race.save()

    await audit(race.tournament_id, "extend_timeout", f"{race.id} extended by {minutes} minutes", user)
    return race.thread_timeout_time


WARN = "warn"
FORFEIT_PENDING = "forfeit_pending"
FORFEIT_IN_PROGRESS = "forfeit_in_progress"


@dataclass
class TimeoutAction:
    """Something the timeout sweep needs the cog to do for one run."""
    race: models.AsyncTournamentRace
    kind: str  # WARN, FORFEIT_PENDING or FORFEIT_IN_PROGRESS
    deadline: datetime.datetime

    @property
    def forfeits(self) -> bool:
        return self.kind != WARN


def pending_timeout_action(race: models.AsyncTournamentRace,
                           now: datetime.datetime) -> Optional[TimeoutAction]:
    """``race.thread_timeout_time`` must be set."""
    deadline = race.thread_timeout_time
    if deadline < now:
        return TimeoutAction(race, FORFEIT_PENDING, deadline)
    if deadline - TIMEOUT_WARNING_LEAD < now:
        return TimeoutAction(race, WARN, deadline)
    return None


def in_progress_timeout_action(race: models.AsyncTournamentRace,
                               now: datetime.datetime) -> Optional[TimeoutAction]:
    if race.start_time is None:
        return None
    deadline = race.start_time + IN_PROGRESS_LIMIT
    if deadline > now:
        return None
    return TimeoutAction(race, FORFEIT_IN_PROGRESS, deadline)


async def find_pending_timeouts(now: Optional[datetime.datetime] = None) -> List[TimeoutAction]:
    """Pending Discord runs that need a warning or a forfeit. Each race has ``user`` fetched."""
    now = now or utcnow()
    actions = []
    races = await models.AsyncTournamentRace.filter(status="pending", thread_id__isnull=False).prefetch_related('user')
    for race in races:
        if race.thread_timeout_time is None:
            race.thread_timeout_time = race.thread_open_time + PENDING_GRACE_PERIOD
            await race.save()
        if action := pending_timeout_action(race, now):
            actions.append(action)
    return actions


async def find_in_progress_timeouts(now: Optional[datetime.datetime] = None) -> List[TimeoutAction]:
    """In-progress Discord runs past the time limit. Each race has ``user`` fetched."""
    now = now or utcnow()
    races = await models.AsyncTournamentRace.filter(status="in_progress",
                                                    thread_id__isnull=False).prefetch_related('user')
    return [a for a in (in_progress_timeout_action(r, now) for r in races) if a]


async def apply_timeout_forfeit(action: TimeoutAction) -> None:
    race = action.race
    race.status = "forfeit"
    await race.save()
    if action.kind == FORFEIT_PENDING:
        details = f"{race.id} was automatically forfeited by System due to timeout"
    else:
        details = f"in progress race \"{race.id}\" was automatically forfeited by System due to timeout"
    await audit(race.tournament_id, "timeout_forfeit", details)


# --- Reattempts (website) ------------------------------------------------------

def _parse_id(value) -> int:
    if value is None:
        raise AsyncTournamentError("You must supply a race_id", 400)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise AsyncTournamentError("race_id must be a number", 400)


async def get_reattemptable_race(tournament: models.AsyncTournament, user: Optional[models.Users],
                                 race_id) -> models.AsyncTournamentRace:
    """The player's run they want to reattempt, if the rules allow it."""
    if user is not None and await models.AsyncTournamentRace.filter(
            user=user, tournament=tournament, reattempted=True).count() >= MAX_REATTEMPTS:
        raise AsyncTournamentError(
            "You have already reattempted a race in this tournament.  Please contact a tournament admin if you "
            "believe this is in error.")

    race_id = _parse_id(race_id)

    race = None
    if user is not None:
        race = await models.AsyncTournamentRace.get_or_none(id=race_id, user=user, tournament=tournament)
    if race is None:
        raise AsyncTournamentError("You must be the player of this race to reattempt it.")
    return race


async def reattempt(tournament: models.AsyncTournament, user: Optional[models.Users], race_id,
                    reason: Optional[str]) -> models.AsyncTournamentRace:
    race = await get_reattemptable_race(tournament, user, race_id)
    race.reattempted = True
    race.reattempt_reason = reason
    await race.save()
    await audit(tournament.id, "reattempt", f"Marked {race.id} as a re-attempt.  Reason: {reason or 'none given'}",
                user)
    return race


# --- Reviews (website) ---------------------------------------------------------

def is_reviewable(race: models.AsyncTournamentRace) -> bool:
    return race.status == "finished" and not race.reattempted


async def get_race_for_review(tournament: models.AsyncTournament, user: Optional[models.Users],
                              race_id: int) -> models.AsyncTournamentRace:
    if not await is_async_tournament_user(user, tournament, ['admin', 'mod']):
        raise AsyncTournamentError("You are not authorized to view this tournament.")

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        raise AsyncTournamentError("Race not found.", 404)
    return race


async def claim_review(race: models.AsyncTournamentRace, reviewer: models.Users) -> bool:
    """Assign an unclaimed, reviewable run to the reviewer who opened it. Returns True if claimed."""
    if race.reviewed_by_id is not None or not is_reviewable(race):
        return False
    race.reviewed_by = reviewer
    await race.save()
    await audit(race.tournament_id, "review_claim", f"{race.id} claimed for review", reviewer)
    return True


async def submit_review(tournament: models.AsyncTournament, reviewer: Optional[models.Users], race_id: int,
                        review_status: str, reviewer_notes: Optional[str]) -> models.AsyncTournamentRace:
    race = await get_race_for_review(tournament, reviewer, race_id)

    if race.status != 'finished':
        raise AsyncTournamentError("This race cannot be reviewed yet.")
    if race.reattempted:
        raise AsyncTournamentError("This race was marked as reattempted and cannot be reviewed.")
    if race.user_id == reviewer.id:
        raise AsyncTournamentError("You are not authorized to review your own tournament run.")

    race.review_status = review_status
    race.reviewer_notes = reviewer_notes
    race.reviewed_at = utcnow()
    race.reviewed_by = reviewer
    await race.save()

    await audit(tournament.id, "review", f"{race.id} reviewed as {review_status}", reviewer)
    return race
