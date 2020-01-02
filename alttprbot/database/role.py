import aiocache

from ..util import orm


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="role")
async def get_role_by_group_emoji(channel_id, message_id, emoji, guild_id):
    roles = await orm.select(
        'SELECT rr.role_id from reaction_group rg LEFT JOIN reaction_role rr ON rr.reaction_group_id = rg.id WHERE rg.channel_id=%s AND rg.message_id=%s AND rg.guild_id=%s and rr.emoji=%s;',
        [channel_id, message_id, guild_id, emoji]
    )
    return roles


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="role")
async def get_guild_groups(guild_id):
    groups = await orm.select(
        'SELECT * from reaction_group WHERE guild_id=%s;',
        [guild_id]
    )
    return groups


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="role")
async def get_guild_group_by_id(reaction_group_id, guild_id):
    groups = await orm.select(
        'SELECT * from reaction_group WHERE id=%s AND guild_id=%s;',
        [reaction_group_id, guild_id]
    )
    return groups


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="role")
async def get_group_roles(reaction_group_id, guild_id):
    roles = await orm.select(
        'SELECT * from reaction_role where reaction_group_id=%s AND guild_id=%s;',
        [reaction_group_id, guild_id]
    )
    return roles


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="role")
async def get_role(reaction_role_id, guild_id):
    role = await orm.select(
        'SELECT * from reaction_role where id = %s and guild_id = %s;',
        [reaction_role_id, guild_id]
    )
    return role[0]


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="role")
async def get_role_group(reaction_role_id, guild_id):
    role = await orm.select(
        'SELECT rg.id, rg.guild_id, rg.channel_id, rg.message_id, rr.emoji '
        'from reaction_group rg '
        'LEFT JOIN reaction_role rr '
        'ON rr.reaction_group_id = rg.id '
        'WHERE rr.id=%s AND rr.guild_id=%s;',
        [reaction_role_id, guild_id]
    )
    return role


async def create_group(guild_id, channel_id, message_id, name, description, bot_managed: int):
    existing_groups = await orm.select(
        'SELECT id from reaction_group WHERE channel_id = %s and message_id=%s and guild_id = %s;',
        [channel_id, message_id, guild_id]
    )

    if len(existing_groups) > 0:
        raise Exception('Group already exists for specified message.')

    await orm.execute(
        'INSERT into reaction_group (`guild_id`,`channel_id`,`message_id`,`name`,`description`,`bot_managed`) values (%s, %s, %s, %s, %s, %s)',
        [guild_id, channel_id, message_id, name, description, bot_managed]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def delete_group(guild_id, group_id):
    await orm.execute(
        'DELETE FROM reaction_group WHERE guild_id=%s AND id=%s',
        [guild_id, group_id]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def update_group(guild_id, group_id, name, description):
    await orm.execute(
        'UPDATE reaction_group SET name=%s, description=%s WHERE guild_id=%s AND id=%s',
        [name, description, guild_id, group_id]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def create_role(guild_id, reaction_group_id, role_id, name, emoji, description, protect_mentions: int):
    ids = await orm.select(
        'SELECT id from reaction_group WHERE id = %s and guild_id = %s;',
        [reaction_group_id, guild_id]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")

    existing_roles = await orm.select(
        'SELECT id from reaction_role WHERE emoji = %s and reaction_group_id = %s',
        [emoji, ids[0]['id']]
    )
    # do something else if this already exists
    if len(existing_roles) > 0:
        raise Exception('Emoji already exists on group.')

    await orm.execute(
        'INSERT into reaction_role (`guild_id`, `reaction_group_id`, `role_id`, `name`, `emoji`, `description`, `protect_mentions`) values (%s, %s, %s, %s, %s, %s, %s)',
        [guild_id, reaction_group_id, role_id, name, emoji, description, protect_mentions]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def delete_role(guild_id, role_id):
    await orm.execute(
        'DELETE FROM reaction_role WHERE guild_id=%s AND id=%s',
        [guild_id, role_id]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def update_role(guild_id, role_id, name, description, protect_mentions: int):
    await orm.execute(
        'UPDATE reaction_role SET name=%s, description=%s, protect_mentions=%s WHERE guild_id=%s AND id=%s',
        [name, description, protect_mentions, guild_id, role_id]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="role")


async def increment_mention_count(guild_id, role_id):
    await orm.execute(
        'INSERT INTO mention_counters(guild_id,role_id) VALUES (%s,%s) ON DUPLICATE KEY UPDATE counter = counter+1;',
        [guild_id, role_id]
    )
