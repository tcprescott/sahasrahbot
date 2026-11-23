"""
Privileged gateway intent handling for SahasrahBot's Discord clients.

Discord's privileged intents (members, presences, message_content) must be
approved for each bot application. When they are not approved, requesting them
makes the gateway close the connection (code 4014) and the bot never comes
online. This module lets each bot run with or without them, controlled by
config flags, and provides member lookup helpers that fall back to REST /
targeted gateway queries (which do not need the members intent) when the
member cache cannot be filled by chunking.

Config flags (module-level constants in ``config.py``; both default to False):

* ``DISCORD_PRIVILEGED_INTENTS`` - main SahasrahBot client.  When True it
  requests the ``members`` intent, as it did before.
* ``AUDIT_DISCORD_PRIVILEGED_INTENTS`` - audit bot.  When True it uses
  ``discord.Intents.all()`` as before.  Defaults to the value of
  ``DISCORD_PRIVILEGED_INTENTS`` if not set.

To restore the previous behaviour once Discord re-approves the intents, set the
flag(s) to True in ``config.py`` and restart.
"""
import logging
from typing import List, Optional

import discord

import config

logger = logging.getLogger(__name__)


def main_bot_privileged_intents_enabled() -> bool:
    return bool(getattr(config, 'DISCORD_PRIVILEGED_INTENTS', False))


def audit_bot_privileged_intents_enabled() -> bool:
    return bool(getattr(config, 'AUDIT_DISCORD_PRIVILEGED_INTENTS', main_bot_privileged_intents_enabled()))


def main_bot_intents() -> discord.Intents:
    intents = discord.Intents.default()
    if main_bot_privileged_intents_enabled():
        intents.members = True  # pylint: disable=assigning-non-slot
    else:
        logger.warning(
            "DISCORD_PRIVILEGED_INTENTS is disabled: SahasrahBot is running without the members intent. "
            "Role-membership features are disabled and member lookups fall back to the REST API."
        )
    return intents


def audit_bot_intents() -> discord.Intents:
    if audit_bot_privileged_intents_enabled():
        return discord.Intents.all()

    logger.warning(
        "AUDIT_DISCORD_PRIVILEGED_INTENTS is disabled: the audit bot is running without the members, presences "
        "and message_content intents. Message content logging, link/ROM moderation and member join/leave "
        "logging are disabled."
    )
    return discord.Intents.default()


def _intents_for(obj) -> Optional[discord.Intents]:
    """Best-effort lookup of the intents a guild's client was started with."""
    state = getattr(obj, '_state', None)
    return getattr(state, '_intents', None)


def members_intent_enabled(guild: discord.Guild) -> bool:
    intents = _intents_for(guild)
    return bool(intents and intents.members)


def message_content_intent_enabled(client: discord.Client) -> bool:
    return bool(client.intents.message_content)


async def ensure_chunked(guild: discord.Guild) -> bool:
    """
    Chunk the guild if the members intent is enabled and it isn't already chunked.

    Returns True if the member cache is (now) complete, False if it cannot be
    filled because the members intent is disabled.
    """
    if not members_intent_enabled(guild):
        return False
    if guild.chunked is False:
        await guild.chunk(cache=True)
    return True


async def get_member(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    """
    Get a guild member by ID.  Uses the cache (chunking first if possible) and
    falls back to the REST API when the cache cannot be complete.
    """
    if guild is None or user_id is None:
        return None
    user_id = int(user_id)

    complete = await ensure_chunked(guild)
    member = guild.get_member(user_id)
    if member is not None or complete:
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
    Equivalent of ``guild.get_member_named``.  Without the members intent this
    uses a targeted gateway member query (allowed without the intent).
    """
    if guild is None or not name:
        return None

    complete = await ensure_chunked(guild)
    member = guild.get_member_named(name)
    if member is not None or complete:
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


async def get_role_members(role: discord.Role) -> Optional[List[discord.Member]]:
    """
    Return the members of a role, or None when that cannot be determined
    because the members intent is disabled.  Discord offers no way to list a
    role's (or guild's) members without the members intent.
    """
    if not await ensure_chunked(role.guild):
        return None
    return role.members


async def get_role_members_or_reply(interaction: discord.Interaction, role: discord.Role,
                                    extra: str = '') -> Optional[List[discord.Member]]:
    """
    Like get_role_members, but sends an ephemeral followup explaining the feature is
    unavailable (and returns None) when role members can't be listed.
    """
    role_members = await get_role_members(role)
    if role_members is None:
        await interaction.followup.send(ROLE_MEMBERS_UNAVAILABLE + extra, ephemeral=True)
    return role_members


ROLE_MEMBERS_UNAVAILABLE = (
    "This feature is temporarily unavailable: listing the members of a role needs the Discord "
    "server members intent, which is currently disabled for SahasrahBot."
)
