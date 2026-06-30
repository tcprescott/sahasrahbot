"""Web presentation adapter for authorization.

Builds the surface-agnostic :class:`~alttprbot.services.AuthSubject` for the web
BFF (the Policy Information Point): from an already-resolved ``Users`` row plus a
guild for role-based checks, or directly from the Discord OAuth session. Resolving
a user's live guild roles needs the ``discordbot`` singleton, which is a
presentation concern — the service decides against the resulting plain data.
"""

from typing import Optional

from alttprbot.services import AuthSubject, UserService
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


async def subject_with_guild_roles(user, guild_id: int) -> AuthSubject:
    """Build a subject for an already-resolved ``Users`` row (or ``None``),
    resolving their live roles in ``guild_id`` for role-based authorization."""
    role_ids = frozenset()
    if user is not None:
        role_ids = await _resolve_discord_role_ids(guild_id, user.discord_user_id)
    return AuthSubject(
        discord_user_id=user.discord_user_id if user else None,
        discord_role_ids=role_ids,
        user=user,
    )


async def subject_from_session(*, with_roles_for_guild: Optional[int] = None) -> AuthSubject:
    """Build a subject from the Discord OAuth session.

    Returns an identity-less subject if the request is unauthenticated. ``discord``
    is imported lazily to avoid a module-load cycle with ``web.web``.
    """
    from alttprbot.presentation.web.web import discord
    from alttprbot.presentation.web.oauth_client import Unauthorized

    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return AuthSubject()

    user = await UserService().get_by_discord_id(discord_user.id)
    role_ids = frozenset()
    if with_roles_for_guild is not None:
        role_ids = await _resolve_discord_role_ids(with_roles_for_guild, discord_user.id)
    return AuthSubject(
        discord_user_id=discord_user.id,
        discord_role_ids=role_ids,
        user=user,
    )
