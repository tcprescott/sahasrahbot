"""Events published by the scheduled jobs, and a stand-in event bus.

TEMPORARY SHIM. The project is adding an event bridge in ``alttprbot/events/`` with the
same API (``Event`` dataclasses with a ``name``, a synchronous non-blocking ``publish``,
``subscribe``/``unsubscribe`` with tokens, ``drain`` for tests). Until it lands, this
module provides that API so the scheduled jobs can already publish events instead of
calling Discord. When it lands, the event classes move to ``alttprbot/events/types.py``
and this module is replaced by imports from ``alttprbot.events``.

Nothing here may import Discord, racetime or the web app.
"""
import asyncio
import dataclasses
import datetime
import itertools
import logging
from typing import Awaitable, Callable, Optional, Union

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Event:
    name = "event"


@dataclasses.dataclass(frozen=True)
class DailyChallengeAvailable(Event):
    """A new alttpr.com daily challenge was published."""
    name = "daily.challenge_available"
    hash_id: str


@dataclasses.dataclass(frozen=True)
class TournamentRoomCreationFailed(Event):
    """Automatically opening a racetime room for a SpeedGaming episode failed."""
    name = "tournament.room_creation_failed"
    event_slug: str
    episode_id: int
    error: str


@dataclasses.dataclass(frozen=True)
class RaceSubmissionReminderFailed(Event):
    """Sending the race submission form reminder for an episode failed."""
    name = "tournament.submission_reminder_failed"
    event_slug: str
    episode_id: int
    error: str


@dataclasses.dataclass(frozen=True)
class StaffNeed:
    """One episode that still needs ``count`` more volunteers of a role."""
    start_time: datetime.datetime
    count: int
    signup_url: str


@dataclasses.dataclass(frozen=True)
class SchedulingNeedsUpdated(Event):
    """The restream crew still needed for an event's upcoming episodes."""
    name = "tournament.scheduling_needs_updated"
    event_slug: str
    commentators: tuple[StaffNeed, ...]
    trackers: tuple[StaffNeed, ...]
    broadcasters: tuple[StaffNeed, ...]


@dataclasses.dataclass(frozen=True)
class TournamentEpisodesRefreshed(Event):
    """The event's SpeedGaming episodes for the next week, as SpeedGaming returned them."""
    name = "tournament.episodes_refreshed"
    event_slug: str
    episodes: tuple[dict, ...]


@dataclasses.dataclass(frozen=True)
class UnmatchedPlayersFound(Event):
    """SpeedGaming players in upcoming episodes who couldn't be found in the event's guild."""
    name = "tournament.unmatched_players_found"
    event_slug: str
    messages: tuple[str, ...]


Handler = Callable[[Event], Awaitable[None]]
EventTypes = Union[type[Event], tuple[type[Event], ...]]

_subscribers: dict[int, tuple[tuple[type[Event], ...], Handler]] = {}
_token_counter = itertools.count(1)
_pending: set[asyncio.Task] = set()


def subscribe(event_types: EventTypes, handler: Handler) -> int:
    if not isinstance(event_types, tuple):
        event_types = (event_types,)
    token = next(_token_counter)
    _subscribers[token] = (event_types, handler)
    return token


def unsubscribe(token: int) -> None:
    _subscribers.pop(token, None)


def publish(event: Event) -> None:
    """Deliver ``event`` to its subscribers in the background. Never raises."""
    try:
        handlers = [h for types, h in list(_subscribers.values()) if isinstance(event, types)]
        if not handlers:
            logger.debug("No subscribers for %s", event.name)
            return
        loop = asyncio.get_running_loop()
        for handler in handlers:
            task = loop.create_task(_deliver(handler, event))
            _pending.add(task)
            task.add_done_callback(_pending.discard)
    except Exception:
        logger.exception("Could not publish %s", getattr(event, "name", event))


async def drain(timeout: Optional[float] = None) -> None:
    """Wait for every delivery in flight. For tests."""
    while _pending:
        await asyncio.wait(set(_pending), timeout=timeout)
        if timeout is not None:
            return


async def _deliver(handler: Handler, event: Event) -> None:
    try:
        await handler(event)
    except Exception:
        logger.exception("Subscriber %r failed handling %s", handler, event.name)
