from typing import List

from alttprbot.services import AsyncTournamentService
from alttprbot.presentation.discord.bot import discordbot


async def is_async_tournament_user(user, tournament, roles: List[str]):
    if 'public' in roles and not tournament.active:
        return True

    if user is None:
        return False

    service = AsyncTournamentService()
    if await service.user_has_permission(tournament, user, roles):
        return True

    guild = discordbot.get_guild(tournament.guild_id)
    if guild.chunked is False:
        await guild.chunk(cache=True)
    member = guild.get_member(user.discord_user_id)
    if member is None:
        return False

    discord_role_ids = [r.id for r in member.roles]
    if await service.role_has_permission(tournament, discord_role_ids, roles):
        return True

    return False
