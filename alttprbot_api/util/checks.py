from typing import List

from alttprbot import models
from alttprbot.util import discord_intents
from alttprbot_discord.bot import discordbot


async def is_async_tournament_user(user: models.Users, tournament: models.AsyncTournament, roles: List[str]):
    if 'public' in roles and not tournament.active:
        return True

    if user is None:
        return False

    authorized = await tournament.permissions.filter(user=user, role__in=roles)
    if authorized:
        return True

    guild = discordbot.get_guild(tournament.guild_id)
    # chunks the guild when the members intent is enabled, otherwise fetches the member via REST
    member = await discord_intents.get_member(guild, user.discord_user_id)
    if member is None:
        return False

    discord_role_ids = [r.id for r in member.roles]
    s = tournament.permissions.filter(discord_role_id__in=discord_role_ids, role__in=roles)
    authorized = await s
    if authorized:
        return True

    return False
