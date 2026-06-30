"""Unit tests for the discord authorization adapter (subject builder + predicates)."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alttprbot.presentation.discord.util import authz


def _interaction(*, owner=False, admin=False, in_guild=True, chunked=True, member_roles=(7, 8)):
    interaction = MagicMock()
    interaction.client.is_owner = AsyncMock(return_value=owner)

    user = MagicMock()
    user.id = 123
    user.created_at = datetime.datetime(2020, 1, 1)
    user.guild_permissions.administrator = admin
    interaction.user = user

    if in_guild:
        guild = MagicMock()
        guild.id = 555
        guild.chunked = chunked
        guild.chunk = AsyncMock()
        resolved = MagicMock()
        resolved.roles = [MagicMock(id=r) for r in member_roles]
        guild.get_member.return_value = resolved
        interaction.guild = guild
    else:
        interaction.guild = None
    return interaction


def _predicate(decorator):
    """Pull the predicate off a plain coro that the app_commands.check decorated."""
    async def dummy(interaction):
        return None

    decorator(dummy)
    return dummy.__discord_app_commands_checks__[0]


# --- subject builder --------------------------------------------------------

async def test_subject_minimal_skips_roles_and_user():
    subject = await authz.subject_from_interaction(_interaction())
    assert subject.discord_user_id == 123
    assert subject.guild_id == 555
    assert subject.discord_role_ids == frozenset()
    assert subject.user is None
    assert subject.account_created_at == datetime.datetime(2020, 1, 1)


async def test_subject_with_roles_chunks_unchunked_guild():
    interaction = _interaction(chunked=False)
    subject = await authz.subject_from_interaction(interaction, with_roles=True)
    interaction.guild.chunk.assert_awaited_once()
    assert subject.discord_role_ids == frozenset({7, 8})


async def test_subject_with_user_resolves_users_row():
    interaction = _interaction()
    with patch.object(authz, "UserService") as user_service:
        user_service.return_value.get_or_create_by_discord_id = AsyncMock(return_value="USERROW")
        subject = await authz.subject_from_interaction(interaction, with_user=True)
    assert subject.user == "USERROW"


# --- platform predicates ----------------------------------------------------

async def test_requires_bot_owner():
    predicate = _predicate(authz.requires_bot_owner("nope"))
    assert await predicate(_interaction(owner=True)) is True
    with pytest.raises(authz.AuthzCheckFailure, match="nope"):
        await predicate(_interaction(owner=False))


async def test_requires_admin_or_owner():
    predicate = _predicate(authz.requires_admin_or_owner("denied"))
    assert await predicate(_interaction(owner=False, admin=True)) is True
    assert await predicate(_interaction(owner=True, admin=False)) is True
    with pytest.raises(authz.AuthzCheckFailure, match="denied"):
        await predicate(_interaction(owner=False, admin=False))
