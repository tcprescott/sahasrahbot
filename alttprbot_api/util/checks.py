from typing import List

from alttprbot import models
from alttprbot_discord.bot import discordbot


async def is_async_tournament_user(user: models.Users, tournament: models.AsyncTournament, roles: List[str]):
    if 'public' in roles and not tournament.active:
        return True

    authorized = await tournament.permissions.filter(user=user, role__in=roles)
    if authorized:
        return True

    guild = discordbot.get_guild(tournament.guild_id)
    if guild.chunked is False:
        await guild.chunk(cache=True)
    member = guild.get_member(user.discord_user_id)
    if member is None:
        return False

    discord_role_ids = [r.id for r in member.roles]
    s = tournament.permissions.filter(discord_role_id__in=discord_role_ids, role__in=roles)
    authorized = await s
    if authorized:
        return True

    return False
