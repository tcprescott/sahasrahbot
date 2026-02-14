import aiocache

from alttprbot.exceptions import SahasrahBotException
from alttprbot.models import ReactionGroup, ReactionRole

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)


async def get_role_by_group_emoji(channel_id, message_id, emoji, guild_id):
    roles = await ReactionRole.filter(
        reaction_group__channel_id=channel_id,
        reaction_group__message_id=message_id,
        reaction_group__guild_id=guild_id,
        guild_id=guild_id,
        emoji=emoji
    ).values('role_id')
    return roles


async def get_guild_groups(guild_id):
    groups = await ReactionGroup.filter(
        guild_id=guild_id
    ).values(
        'id', 'guild_id', 'channel_id', 'message_id', 'name', 'description', 'bot_managed'
    )
    return groups


async def get_guild_group_by_id(reaction_group_id, guild_id):
    groups = await ReactionGroup.filter(
        id=reaction_group_id,
        guild_id=guild_id
    ).values(
        'id', 'guild_id', 'channel_id', 'message_id', 'name', 'description', 'bot_managed'
    )
    return groups


async def get_group_roles(reaction_group_id, guild_id):
    roles = await ReactionRole.filter(
        reaction_group_id=reaction_group_id,
        guild_id=guild_id
    ).values(
        'id',
        'guild_id',
        'reaction_group_id',
        'role_id',
        'name',
        'emoji',
        'description',
        'protect_mentions'
    )
    return roles


async def get_role(reaction_role_id, guild_id):
    role = await ReactionRole.filter(
        id=reaction_role_id,
        guild_id=guild_id
    ).values(
        'id',
        'guild_id',
        'reaction_group_id',
        'role_id',
        'name',
        'emoji',
        'description',
        'protect_mentions'
    )
    return role[0]


async def get_role_group(reaction_role_id, guild_id):
    role = await ReactionRole.filter(
        id=reaction_role_id,
        guild_id=guild_id
    ).values(
        'reaction_group_id',
        'reaction_group__guild_id',
        'reaction_group__channel_id',
        'reaction_group__message_id',
        'emoji'
    )
    return [{
        'id': item['reaction_group_id'],
        'guild_id': item['reaction_group__guild_id'],
        'channel_id': item['reaction_group__channel_id'],
        'message_id': item['reaction_group__message_id'],
        'emoji': item['emoji']
    } for item in role]


async def create_group(guild_id, channel_id, message_id, name, description, bot_managed: int):
    existing_groups = await ReactionGroup.filter(
        channel_id=channel_id,
        message_id=message_id,
        guild_id=guild_id
    ).values('id')

    if len(existing_groups) > 0:
        raise SahasrahBotException(
            'Group already exists for specified message.')

    await ReactionGroup.create(
        guild_id=guild_id,
        channel_id=channel_id,
        message_id=message_id,
        name=name,
        description=description,
        bot_managed=bot_managed
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def delete_group(guild_id, group_id):
    await ReactionGroup.filter(guild_id=guild_id, id=group_id).delete()
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def update_group(guild_id, group_id, name, description):
    await ReactionGroup.filter(guild_id=guild_id, id=group_id).update(name=name, description=description)
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def create_role(guild_id, reaction_group_id, role_id, name, emoji, description, protect_mentions: int):
    ids = await ReactionGroup.filter(
        id=reaction_group_id,
        guild_id=guild_id
    ).values('id')
    if len(ids) == 0:
        raise SahasrahBotException('Invalid group for this guild.')

    existing_roles = await ReactionRole.filter(
        emoji=emoji,
        reaction_group_id=ids[0]['id']
    ).values('id')

    if len(existing_roles) > 0:
        raise SahasrahBotException('Emoji already exists on group.')

    await ReactionRole.create(
        guild_id=guild_id,
        reaction_group_id=reaction_group_id,
        role_id=role_id,
        name=name,
        emoji=emoji,
        description=description,
        protect_mentions=protect_mentions
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def delete_role(guild_id, role_id):
    await ReactionRole.filter(guild_id=guild_id, id=role_id).delete()
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def update_role(guild_id, role_id, name, description, protect_mentions: int):
    await ReactionRole.filter(guild_id=guild_id, id=role_id).update(
        name=name,
        description=description,
        protect_mentions=protect_mentions
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")
