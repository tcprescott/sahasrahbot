"""Discord implementations of the lookups that services in ``alttprbot/`` need.

Services don't import the bot. ``sahasrahbot.py`` calls ``register()`` at startup,
which hands each service the Discord-backed function it asks for.
"""

from typing import List, Optional

from alttprbot.services import asynctournament as asynctournament_service
from alttprbot.util import discord_members
from alttprbot_discord.bot import discordbot


async def member_role_ids(guild_id: int, discord_user_id: int) -> Optional[List[int]]:
    """Role IDs of a guild member, or None if the guild or member can't be found."""
    guild = discordbot.get_guild(guild_id)
    if guild is None:
        return None
    member = await discord_members.get_member(guild, discord_user_id)
    if member is None:
        return None
    return [r.id for r in member.roles]


def register() -> None:
    asynctournament_service.set_member_role_lookup(member_role_ids)
