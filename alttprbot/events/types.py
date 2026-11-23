"""Every event SahasrahBot publishes.

One frozen dataclass per event, named for what happened, not for who should be
told. Add a new event here and to ``ALL_EVENTS``; ``tests/test_events.py``
checks that every class is listed, named ``object.verb`` and unique.
"""

import dataclasses
from datetime import datetime
from typing import Optional

from alttprbot.events.event import Event

_frozen = dataclasses.dataclass(frozen=True, kw_only=True)


# --- racetime.gg rooms ------------------------------------------------------

@_frozen
class RaceStatusChanged(Event):
    """A racetime.gg room the bot is in moved to a new status.

    ``status`` is racetime's value: ``open``, ``invitational``, ``pending``,
    ``in_progress``, ``finished`` or ``cancelled``. ``base_url`` is the racetime
    host (``https://racetime.gg``), so a subscriber can build profile links.
    """
    name = "race.status_changed"

    category: str
    room_name: str
    room_url: str
    base_url: str
    status: str
    entrant_ids: tuple[str, ...] = ()


# --- tournament and daily race rooms ----------------------------------------

@_frozen
class TournamentRoomOpened(Event):
    """The bot opened a race room for a scheduled SpeedGaming episode.

    ``player_discord_ids`` is empty for open races such as the SG dailies.
    ``seed_time`` is set only for races that announce when the seed goes out.
    """
    name = "tournament.room_opened"

    event_slug: str
    episode_id: int
    room_name: str
    room_url: str
    title: str
    versus: str = ""
    start_time: Optional[datetime] = None
    seed_time: Optional[datetime] = None
    broadcast_channels: tuple[str, ...] = ()
    player_discord_ids: tuple[int, ...] = ()


# --- ranked choice elections ------------------------------------------------

@_frozen
class RankedChoiceBallotCast(Event):
    """Someone submitted a ballot in a ranked choice election."""
    name = "ranked_choice.ballot_cast"

    election_id: int


# --- scheduled jobs (published by the scheduler service) --------------------

@_frozen
class DailyChallengeAvailable(Event):
    """A new ALTTPR daily challenge seed is out."""
    name = "daily.challenge_available"

    hash_id: str


@_frozen
class TournamentRoomCreationFailed(Event):
    """Opening the race room for a scheduled episode failed."""
    name = "tournament.room_creation_failed"

    event_slug: str
    episode_id: int
    error: str


@_frozen
class RaceSubmissionReminderFailed(Event):
    """Sending the settings-submission reminder for an episode failed."""
    name = "tournament.submission_reminder_failed"

    event_slug: str
    episode_id: int
    error: str


@_frozen
class SchedulingNeedsUpdated(Event):
    """The list of upcoming episodes short on restream crew was recomputed."""
    name = "tournament.scheduling_needs_updated"

    event_slug: str
    needs: tuple = ()


@_frozen
class TournamentEpisodesRefreshed(Event):
    """Upcoming SpeedGaming episodes for an event were fetched again."""
    name = "tournament.episodes_refreshed"

    event_slug: str
    episodes: tuple = ()


@_frozen
class UnmatchedPlayersFound(Event):
    """Scheduled players could not be matched to a Discord or racetime account."""
    name = "tournament.unmatched_players_found"

    event_slug: str
    messages: tuple[str, ...] = ()


ALL_EVENTS: tuple[type[Event], ...] = (
    RaceStatusChanged,
    TournamentRoomOpened,
    RankedChoiceBallotCast,
    DailyChallengeAvailable,
    TournamentRoomCreationFailed,
    RaceSubmissionReminderFailed,
    SchedulingNeedsUpdated,
    TournamentEpisodesRefreshed,
    UnmatchedPlayersFound,
)
