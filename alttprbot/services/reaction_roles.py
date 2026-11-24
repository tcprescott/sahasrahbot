"""Reaction roles: a group is one Discord message; reacting to it with a role's emoji grants that role.

The ``reaction_group`` and ``reaction_role`` tables. Every lookup is scoped to the guild
that owns the group or role. Callers pass ids and plain values, never Discord objects.
"""

from typing import List, Optional

from alttprbot import models
from alttprbot.exceptions import SahasrahBotException

MAX_ROLES_PER_GROUP = 20


async def role_ids_for_reaction(guild_id: int, channel_id: int, message_id: int, emoji: str) -> List[int]:
    """Discord role ids granted by reacting with ``emoji`` to the given message."""
    return await models.ReactionRole.filter(
        reaction_group__guild_id=guild_id,
        reaction_group__channel_id=channel_id,
        reaction_group__message_id=message_id,
        emoji=emoji,
    ).values_list('role_id', flat=True)


async def list_groups(guild_id: int) -> List[models.ReactionGroup]:
    return await models.ReactionGroup.filter(guild_id=guild_id)


async def get_group(group_id: int, guild_id: int) -> Optional[models.ReactionGroup]:
    return await models.ReactionGroup.get_or_none(id=group_id, guild_id=guild_id)


async def require_group(group_id: int, guild_id: int) -> models.ReactionGroup:
    group = await get_group(group_id, guild_id)
    if group is None:
        raise SahasrahBotException('Reaction group not found.')
    return group


async def group_roles(group_id: int, guild_id: int) -> List[models.ReactionRole]:
    return await models.ReactionRole.filter(reaction_group_id=group_id, guild_id=guild_id)


async def require_role(role_id: int, guild_id: int) -> models.ReactionRole:
    """The reaction role with its ``reaction_group`` fetched."""
    role = await models.ReactionRole.get_or_none(id=role_id, guild_id=guild_id).prefetch_related('reaction_group')
    if role is None:
        raise SahasrahBotException('Reaction role not found.')
    return role


async def create_group(guild_id: int, channel_id: int, message_id: int, name: str,
                       description: Optional[str], bot_managed: bool) -> models.ReactionGroup:
    if await models.ReactionGroup.exists(channel_id=channel_id, message_id=message_id, guild_id=guild_id):
        raise SahasrahBotException('Group already exists for specified message.')

    return await models.ReactionGroup.create(
        guild_id=guild_id,
        channel_id=channel_id,
        message_id=message_id,
        name=name,
        description=description,
        bot_managed=int(bot_managed),
    )


async def update_group(guild_id: int, group_id: int, name: str, description: Optional[str]) -> None:
    await models.ReactionGroup.filter(guild_id=guild_id, id=group_id).update(name=name, description=description)


async def delete_group(guild_id: int, group_id: int) -> None:
    """Delete the group; its roles go with it (the foreign key cascades)."""
    await models.ReactionGroup.filter(guild_id=guild_id, id=group_id).delete()


async def create_role(guild_id: int, group_id: int, role_id: int, name: str, emoji: str,
                      description: Optional[str], protect_mentions: bool) -> models.ReactionRole:
    if len(await group_roles(group_id, guild_id)) >= MAX_ROLES_PER_GROUP:
        raise SahasrahBotException(
            f'No more than {MAX_ROLES_PER_GROUP} roles can be on a group.  Please create a new group.')

    group = await require_group(group_id, guild_id)

    if await models.ReactionRole.exists(emoji=emoji, reaction_group_id=group.id):
        raise SahasrahBotException('Emoji already exists on group.')

    return await models.ReactionRole.create(
        guild_id=guild_id,
        reaction_group_id=group.id,
        role_id=role_id,
        name=name,
        emoji=emoji,
        description=description,
        protect_mentions=int(protect_mentions),
    )


async def update_role(guild_id: int, role_id: int, name: str, description: Optional[str],
                      protect_mentions: bool) -> None:
    await models.ReactionRole.filter(guild_id=guild_id, id=role_id).update(
        name=name, description=description, protect_mentions=int(protect_mentions))


async def delete_role(guild_id: int, role_id: int) -> None:
    await models.ReactionRole.filter(guild_id=guild_id, id=role_id).delete()
