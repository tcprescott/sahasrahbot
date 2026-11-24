"""SM and SMZ3 multiworld sign-ups (the ``/smmulti`` Discord command).

A multiworld game is keyed by the id of the Discord message that hosts its sign-up
view. Only the owner (the member who ran the command) may choose the randomizer and
preset, start or cancel it; anyone may join or leave.

Callers pass ids and plain values, never Discord objects. Rule violations raise
``MultiworldNotAuthorized`` or ``MultiworldNotReady``; the cog turns them into replies.
"""

from typing import List

from alttprbot import models
from alttprbot.alttprgen.smz3multi import generate_multiworld
from alttprbot.exceptions import SahasrahBotException

MIN_PLAYERS = 2

STATUS_OPEN = "STARTED"
STATUS_CLOSED = "CLOSED"
STATUS_CANCELLED = "CANCELLED"


class MultiworldNotAuthorized(SahasrahBotException):
    """The user is not the game's owner."""


class MultiworldNotReady(SahasrahBotException):
    """The randomizer or preset has not been chosen yet."""


async def create(message_id: int, owner_id: int) -> models.Multiworld:
    return await models.Multiworld.create(message_id=message_id, owner_id=owner_id, status=STATUS_OPEN)


async def get(message_id: int) -> models.Multiworld:
    return await models.Multiworld.get(message_id=message_id)


async def _get_owned(message_id: int, user_id: int) -> models.Multiworld:
    multiworld = await get(message_id)
    if not multiworld.owner_id == user_id:
        raise MultiworldNotAuthorized()
    return multiworld


async def set_randomizer(message_id: int, user_id: int, randomizer: str) -> models.Multiworld:
    """Choose the randomizer; this clears any preset chosen for the previous one."""
    multiworld = await _get_owned(message_id, user_id)
    multiworld.randomizer = randomizer
    multiworld.preset = None
    await multiworld.save()
    return multiworld


async def set_preset(message_id: int, user_id: int, preset: str) -> models.Multiworld:
    multiworld = await _get_owned(message_id, user_id)
    multiworld.preset = preset
    await multiworld.save(update_fields=['preset'])
    return multiworld


async def join(message_id: int, user_id: int) -> bool:
    """Sign the user up. False if they were already signed up."""
    multiworld = await get(message_id)
    entrant = await models.MultiworldEntrant.get_or_none(discord_user_id=user_id, multiworld=multiworld)
    if entrant:
        return False
    await models.MultiworldEntrant.create(discord_user_id=user_id, multiworld=multiworld)
    return True


async def leave(message_id: int, user_id: int) -> None:
    """Remove the user's sign-up, if there is one."""
    multiworld = await get(message_id)
    entrant = await models.MultiworldEntrant.get_or_none(discord_user_id=user_id, multiworld=multiworld)
    if entrant:
        await entrant.delete()


async def entrant_ids(message_id: int) -> List[int]:
    """Discord user ids of everyone signed up, in sign-up order."""
    entrants = await models.MultiworldEntrant.filter(multiworld__message_id=message_id)
    return [e.discord_user_id for e in entrants]


async def check_can_start(message_id: int, user_id: int) -> models.Multiworld:
    """Raise unless the user owns the game and both randomizer and preset are chosen."""
    multiworld = await _get_owned(message_id, user_id)
    if not multiworld.randomizer or not multiworld.preset:
        raise MultiworldNotReady()
    return multiworld


def has_enough_players(player_count: int) -> bool:
    return player_count >= MIN_PLAYERS


async def start(multiworld: models.Multiworld, player_names: List[str]):
    """Roll the multiworld seed for ``player_names`` and close the game for entry.

    Returns the seed from ``generate_multiworld`` (its ``url`` is the game room).
    """
    seed = await generate_multiworld(multiworld.preset, player_names, tournament=False,
                                     randomizer=multiworld.randomizer)
    multiworld.status = STATUS_CLOSED
    await multiworld.save()
    return seed


async def cancel(message_id: int, user_id: int) -> models.Multiworld:
    multiworld = await _get_owned(message_id, user_id)
    multiworld.status = STATUS_CANCELLED
    await multiworld.save()
    return multiworld
