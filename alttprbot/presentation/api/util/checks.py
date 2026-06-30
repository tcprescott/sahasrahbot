"""Transitional shim for the async-tournament authorization check.

The decision now lives in ``AuthorizationService.is_async_tournament_user`` (the
service tier). This shim resolves the caller's live Discord roles — a presentation
concern that needs the ``discordbot`` singleton — into an ``AuthSubject`` and
delegates. Callers are migrated to build the subject themselves in later phases,
after which this module is deleted.
"""

from typing import List

from alttprbot.services import AuthorizationService, AuthSubject
from alttprbot.presentation.discord.bot import discordbot


async def _resolve_discord_role_ids(guild_id: int, discord_user_id: int) -> frozenset:
    guild = discordbot.get_guild(guild_id)
    if guild is None:
        return frozenset()
    if guild.chunked is False:
        await guild.chunk(cache=True)
    member = guild.get_member(discord_user_id)
    if member is None:
        return frozenset()
    return frozenset(role.id for role in member.roles)


async def is_async_tournament_user(user, tournament, roles: List[str]):
    role_ids = frozenset()
    if user is not None:
        role_ids = await _resolve_discord_role_ids(tournament.guild_id, user.discord_user_id)
    subject = AuthSubject(
        discord_user_id=user.discord_user_id if user else None,
        discord_role_ids=role_ids,
        user=user,
    )
    return await AuthorizationService().is_async_tournament_user(subject, tournament, roles)
