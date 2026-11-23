"""
Guild member lookups for SahasrahBot's Discord clients.

SahasrahBot does not use any of Discord's privileged gateway intents (members,
presences, message_content).  Without the members intent the member cache is
never complete (guilds can't be chunked), so these helpers check the cache and
then fall back to the REST API or a targeted gateway member query, neither of
which needs the intent.

Listing every member of a guild or role is not possible without the members
intent.
"""
import logging
from typing import Optional

import discord

logger = logging.getLogger(__name__)


async def get_member(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    """Get a guild member by ID from the cache, falling back to the REST API."""
    if guild is None or user_id is None:
        return None
    user_id = int(user_id)

    member = guild.get_member(user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user_id)
    except discord.NotFound:
        return None
    except discord.HTTPException:
        logger.exception("Unable to fetch member %s from guild %s", user_id, guild.id)
        return None


def _matches_name(member: discord.Member, name: str, discriminator: Optional[str]) -> bool:
    if discriminator is not None:
        return member.name == name and member.discriminator == discriminator
    return name in (member.name, member.global_name, member.nick)


async def get_member_named(guild: discord.Guild, name: str) -> Optional[discord.Member]:
    """
    Equivalent of ``guild.get_member_named``, falling back to a targeted gateway
    member query.  Discord's query matches username and server nickname prefixes,
    so a member known only by their global display name may not be found.
    """
    if guild is None or not name:
        return None

    member = guild.get_member_named(name)
    if member is not None:
        return member

    discriminator = None
    username = name
    if len(name) > 5 and name[-5] == '#' and name[-4:].isdigit():
        username, discriminator = name[:-5], name[-4:]

    try:
        results = await guild.query_members(query=username, limit=100, cache=False)
    except (discord.HTTPException, discord.ClientException, TimeoutError):
        logger.exception("Unable to query members named %s in guild %s", name, guild.id)
        return None

    return discord.utils.find(lambda m: _matches_name(m, username, discriminator), results)


ROLE_MEMBERS_UNAVAILABLE = (
    "This command is unavailable: listing the members of a role requires Discord's privileged "
    "server members intent, which SahasrahBot does not use."
)
