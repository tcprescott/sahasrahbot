"""SahasrahBot's in-process event bridge.

Publish from any layer, without importing the Discord bot::

    from alttprbot import events
    events.publish(events.RankedChoiceBallotCast(election_id=election.id))

Subscribe at startup with an async handler::

    events.subscribe(events.RankedChoiceBallotCast, handler)

Discord subscribers live in ``alttprbot_discord/notifications.py`` and are
registered by ``sahasrahbot.py``. See ``bus.py`` for the delivery contract.
"""

from alttprbot.events.bus import clear, drain, publish, subscribe, unsubscribe
from alttprbot.events.event import Event
from alttprbot.events.types import (
    ALL_EVENTS,
    RaceStatusChanged,
    TournamentRoomOpened,
    RankedChoiceBallotCast,
    DailyChallengeAvailable,
    TournamentRoomCreationFailed,
    RaceSubmissionReminderFailed,
    SchedulingNeedsUpdated,
    StaffNeed,
    TournamentEpisodesRefreshed,
    UnmatchedPlayersFound,
)

__all__ = [
    "ALL_EVENTS",
    "Event",
    "clear",
    "drain",
    "publish",
    "subscribe",
    "unsubscribe",
    "RaceStatusChanged",
    "TournamentRoomOpened",
    "RankedChoiceBallotCast",
    "DailyChallengeAvailable",
    "TournamentRoomCreationFailed",
    "RaceSubmissionReminderFailed",
    "SchedulingNeedsUpdated",
    "StaffNeed",
    "TournamentEpisodesRefreshed",
    "UnmatchedPlayersFound",
]
