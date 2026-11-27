"""Inquiry messages: a Discord message with a button that opens a private thread for a
role. This module remembers which role each message is for, and lets a server's
administrators list, post and remove them from the website (the Servers area's
Settings section).

Posting and the channel permission checks need the Discord bot, which registers a
``Poster`` at startup (``alttprbot_discord/inquiries.py``).
"""

from dataclasses import dataclass
from typing import Optional, Protocol

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import audit, discord_directory, servers


@dataclass(frozen=True)
class Check:
    """One thing an inquiry channel needs, and whether it has it."""
    ok: bool
    text: str


class Poster(Protocol):
    async def checks(self, guild_id: int, channel_id: int, role_id: int) -> list[Check]:
        """What the channel and role need for an inquiry button, each passing or not."""

    async def post(self, guild_id: int, channel_id: int, role_id: int) -> int:
        """Post the button message and return its id. Raises ``InvalidInputError``
        with a readable reason when Discord refuses."""

    async def delete(self, channel_id: int, message_id: int) -> None:
        """Delete the message; one that's already gone is fine."""

    async def locate(self, message_id: int, role_id: int) -> Optional[tuple[int, int]]:
        """The (server id, channel id) an older message was posted in, found from its
        role's server, or None when it can't be found."""


_poster: Optional[Poster] = None


def register_poster(poster: Poster) -> None:
    global _poster
    _poster = poster


def _get_poster() -> Poster:
    if _poster is None:
        raise RuntimeError("No inquiry poster registered; call alttprbot_discord.gateways.register() at startup.")
    return _poster


async def register(message_id: int, role_id: int, guild_id: Optional[int] = None,
                   channel_id: Optional[int] = None) -> None:
    await models.InquiryMessageConfig.create(message_id=message_id, role_id=role_id, guild_id=guild_id,
                                             channel_id=channel_id)
    await audit.record(audit.INQUIRY_CREATED, target=f'Message {message_id}', guild_id=guild_id,
                       details={'message_id': message_id, 'role_id': role_id, 'channel_id': channel_id})


async def role_for_message(message_id: int) -> int:
    """The role an inquiry message opens threads for. Raises ``DoesNotExist`` for a
    message that isn't one, as the button always has."""
    config = await models.InquiryMessageConfig.get(message_id=message_id)
    return config.role_id


async def note_location(message_id: int, guild_id: int, channel_id: int) -> None:
    """Record where an inquiry message is, if it didn't know yet. The button calls this
    when pressed, so older messages fill themselves in."""
    updated = await models.InquiryMessageConfig.filter(message_id=message_id, guild_id=None).update(
        guild_id=guild_id, channel_id=channel_id)
    if updated:
        await audit.record(audit.INQUIRY_LOCATED, target=f'Message {message_id}', guild_id=guild_id,
                           details={'message_id': message_id, 'channel_id': channel_id})


# Messages already searched for in this process and not found, so each restart looks
# for them once rather than every run.
_not_found: set[int] = set()


async def locate_older_messages() -> int:
    """Find the server and channel of inquiry messages posted before they were stored
    (migration 103), so they show up on the website. Returns how many were found."""
    poster = _get_poster()
    found = 0
    for row in await models.InquiryMessageConfig.filter(guild_id=None).order_by('message_id'):
        if row.message_id in _not_found:
            continue
        where = await poster.locate(row.message_id, row.role_id)
        if where is None:
            _not_found.add(row.message_id)
            continue
        await note_location(row.message_id, *where)
        found += 1
    return found


# --- the website -------------------------------------------------------------


async def list_for_guild(guild_id: int, user_id: int) -> list[dict]:
    """The server's inquiry buttons that know their server, newest first."""
    await servers.require_admin(guild_id, user_id)
    directory = discord_directory.get()
    channels = {c.id: c.name for c in await directory.text_channels(guild_id)}
    roles = {r.id: r.name for r in await directory.roles(guild_id)}
    rows = await models.InquiryMessageConfig.filter(guild_id=guild_id).order_by('-created', '-message_id')
    return [{
        'message_id': row.message_id,
        'channel_id': row.channel_id,
        'channel_name': channels.get(row.channel_id),
        'role_id': row.role_id,
        'role_name': roles.get(row.role_id),
        'created': row.created,
    } for row in rows]


async def _check_targets(guild_id: int, channel_id: int, role_id: int) -> None:
    directory = discord_directory.get()
    if channel_id not in {c.id for c in await directory.text_channels(guild_id)}:
        raise InvalidInputError("SahasrahBot can't post in that channel. Pick one from the list.")
    if role_id not in {r.id for r in await directory.roles(guild_id)}:
        raise InvalidInputError("That role isn't in this server. Pick one from the list.")


async def check(guild_id: int, user_id: int, channel_id: int, role_id: int) -> list[Check]:
    """Whether an inquiry button would work in that channel for that role."""
    await servers.require_admin(guild_id, user_id)
    await _check_targets(guild_id, channel_id, role_id)
    return await _get_poster().checks(guild_id, channel_id, role_id)


async def post(guild_id: int, user_id: int, channel_id: int, role_id: int) -> dict:
    """Post an inquiry button, once every check passes, and remember it."""
    await servers.require_admin(guild_id, user_id)
    await _check_targets(guild_id, channel_id, role_id)
    poster = _get_poster()
    failing = [c for c in await poster.checks(guild_id, channel_id, role_id) if not c.ok]
    if failing:
        raise InvalidInputError(failing[0].text)
    message_id = await poster.post(guild_id, channel_id, role_id)
    await register(message_id, role_id, guild_id, channel_id)
    return next(i for i in await list_for_guild(guild_id, user_id) if i['message_id'] == message_id)


async def remove(guild_id: int, user_id: int, message_id: int) -> None:
    """Delete an inquiry button's message and forget it. Threads it opened stay."""
    await servers.require_admin(guild_id, user_id)
    row = await models.InquiryMessageConfig.get_or_none(message_id=message_id, guild_id=guild_id)
    if row is None:
        raise NotFoundError("That inquiry button isn't in this server.")
    if row.channel_id:
        await _get_poster().delete(row.channel_id, message_id)
    await row.delete()
    await audit.record(audit.INQUIRY_REMOVED, target=f'Message {message_id}', guild_id=guild_id,
                       details={'message_id': message_id, 'role_id': row.role_id, 'channel_id': row.channel_id})
