"""Per-room racetime.gg state that the race handlers keep in the database:
unlisted rooms the bot must rejoin after a restart, the stream-override whitelist,
and the tournament race a room belongs to.

This is the only module that reads or writes ``models.RTGGUnlistedRooms`` and
``models.RTGGOverrideWhitelist``. Callers pass plain values (room names such as
``alttpr/cool-room-1234``, category slugs, racetime user ids), never a handler or bot.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from alttprbot import models

# Results of stream_override_status()
OVERRIDE_ALLOWED = 'allowed'
OVERRIDE_NOT_WHITELISTED = 'not_whitelisted'
OVERRIDE_EXPIRED = 'expired'


async def set_unlisted(room_name: str, category: str, unlisted: bool) -> None:
    """Remember an unlisted room so the bot rejoins it on startup, or forget it."""
    if unlisted:
        await models.RTGGUnlistedRooms.update_or_create(room_name=room_name, defaults={'category': category})
    else:
        await forget_unlisted(room_name)


async def forget_unlisted(room_name: str) -> None:
    await models.RTGGUnlistedRooms.filter(room_name=room_name).delete()


async def unlisted_rooms(category: str) -> List[models.RTGGUnlistedRooms]:
    """The unlisted rooms remembered for this category (use ``.room_name``)."""
    return await models.RTGGUnlistedRooms.filter(category=category)


async def stream_override_status(racetime_id: str, category: str) -> str:
    """Whether this user may override the streaming requirement in the category:
    OVERRIDE_ALLOWED, OVERRIDE_NOT_WHITELISTED or OVERRIDE_EXPIRED."""
    whitelisted_user = await models.RTGGOverrideWhitelist.get_or_none(racetime_id=racetime_id, category=category)
    if whitelisted_user is None:
        return OVERRIDE_NOT_WHITELISTED
    # ``expires`` comes back timezone-aware (use_tz=True), so compare with an aware now.
    if whitelisted_user.expires is not None and whitelisted_user.expires < datetime.now(timezone.utc):
        return OVERRIDE_EXPIRED
    return OVERRIDE_ALLOWED


async def tournament_race(room_name: str) -> Optional[Tuple[str, str]]:
    """``(event, episode_id)`` of the tournament race played in this room, or None."""
    race = await models.TournamentResults.get_or_none(srl_id=room_name)
    if not race:
        return None
    return race.event, race.episode_id
