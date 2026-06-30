"""Discord presentation adapter for authorization.

Two responsibilities, both at the presentation edge:

* ``subject_from_interaction`` — the Policy Information Point: resolve a discord
  ``Interaction`` (bot owner, guild roles, linked ``Users`` row, account age) into
  the surface-agnostic :class:`~alttprbot.services.AuthSubject` that the service
  decides against.
* platform predicates (``requires_bot_owner``, ``requires_admin_or_owner``) — the
  native, framework-evaluated gates for *platform* identity/permission. Domain
  authorization (tournament roles, ownership, …) is decided by
  ``AuthorizationService``, not here.

App-command checks raise :class:`AuthzCheckFailure` (a ``CheckFailure`` carrying a
user-facing message) so the central ``errors`` cog renders it ephemerally. View /
modal callbacks don't funnel through that handler, so they call the service's
``is_*`` bool methods inline instead.
"""

from __future__ import annotations

import discord
from discord import app_commands

from alttprbot.services import AuthSubject, UserService


class AuthzCheckFailure(app_commands.CheckFailure):
    """An app-command check failure whose ``str()`` is the user-facing message."""


async def subject_from_interaction(
    interaction: discord.Interaction,
    *,
    with_user: bool = False,
    with_roles: bool = False,
) -> AuthSubject:
    """Build an ``AuthSubject`` from a discord interaction.

    ``with_roles`` chunks the guild and resolves the member's role ids (needed for
    role-based tournament authz); ``with_user`` resolves/creates the linked
    ``Users`` row (needed for per-user grants, the join policy, etc.). Both are
    opt-in so trivial checks (e.g. self-ownership) don't pay for a guild chunk.
    """
    member = interaction.user

    role_ids = frozenset()
    if with_roles and interaction.guild is not None:
        if interaction.guild.chunked is False:
            await interaction.guild.chunk(cache=True)
        resolved = interaction.guild.get_member(member.id)
        if resolved is not None:
            role_ids = frozenset(role.id for role in resolved.roles)

    user = None
    if with_user:
        user = await UserService().get_or_create_by_discord_id(member.id)

    return AuthSubject(
        discord_user_id=member.id,
        discord_role_ids=role_ids,
        guild_id=interaction.guild.id if interaction.guild else None,
        account_created_at=member.created_at,
        user=user,
    )


def requires_bot_owner(message: str = "You must be the bot owner to use this command."):
    async def predicate(interaction: discord.Interaction) -> bool:
        if not await interaction.client.is_owner(interaction.user):
            raise AuthzCheckFailure(message)
        return True

    return app_commands.check(predicate)


def requires_admin_or_owner(message: str = "You are not authorized to use this command."):
    async def predicate(interaction: discord.Interaction) -> bool:
        if await interaction.client.is_owner(interaction.user):
            return True
        permissions = getattr(interaction.user, "guild_permissions", None)
        if permissions is not None and permissions.administrator:
            return True
        raise AuthzCheckFailure(message)

    return app_commands.check(predicate)
