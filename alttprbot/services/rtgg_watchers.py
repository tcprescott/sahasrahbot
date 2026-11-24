"""racetime.gg watchers: Discord channels told when a watchlisted player, or a brand
new racer, starts a race in a category.

Callers pass plain values (a category slug, racetime.gg user ids) and get plain data
back.
"""

from dataclasses import dataclass
from typing import Iterable, List

from alttprbot import models


@dataclass(frozen=True)
class WatchlistHit:
    channel_id: int
    racetime_id: str


async def watchlisted_entrants(category: str, racetime_ids: Iterable[str]) -> List[WatchlistHit]:
    """One entry per (watcher channel, entrant) for entrants on a watchlist in this category."""
    rows = await models.RTGGWatcherPlayer.filter(
        racetime_id__in=list(racetime_ids),
        rtgg_watcher__category=category,
    ).prefetch_related("rtgg_watcher")
    return [WatchlistHit(channel_id=row.rtgg_watcher.channel_id, racetime_id=row.racetime_id) for row in rows]


async def new_player_channels(category: str) -> List[int]:
    """Channels that want to hear about first-time racers in this category."""
    watchers = await models.RTGGWatcher.filter(category=category, notify_on_new_player=True)
    return [w.channel_id for w in watchers]
