from ..util import orm

async def get_group(reaction_group_id, guild_id):
    messages = await orm.select(
        'SELECT * from reaction_group WHERE id=%s AND guild_id=%s;',
        [reaction_group_id, guild_id]
    )
    return messages[0]

async def get_guild_groups(guild_id):
    groups = await orm.select(
        'SELECT * from reaction_group WHERE guild_id=%s;',
        [guild_id]
    )
    return groups

async def get_group_roles(reaction_group_id, guild_id):
    roles = await orm.select(
        'SELECT * from reaction_role where reaction_group_id=%s AND guild_id=%s ORDER BY `order` DESC;',
        [reaction_group_id, guild_id]
    )
    return roles

async def get_role(reaction_role_id, guild_id):
    role = await orm.select(
        'SELECT * from reaction_role where id = %s and guild_id = %s;',
        [reaction_role_id]
    )
    return role[0]

async def create_group(guild_id, channel_id, message_id, name, description, bot_managed):
    await orm.execute(
        'INSERT into reaction_group (`guild_id`,`channel_id`,`message_id`,`name`,`description`,`bot_managed`) values (%s, %s, %s, %s, %s, %s)',
        [guild_id, channel_id, message_id, name, description, bot_managed]
    )

async def create_role(guild_id, reaction_group_id, role_id, name, emoji):
    ids = await orm.select(
        'SELECT id from reaction_group WHERE id = %s and guild_id = %s;',
        [reaction_group_id,guild_id]
    )

    existing_roles = await orm.select(
        'SELECT id from reaction_role WHERE emoji = %s and reaction_group_id = %s',
        [emoji, ids[0]['id']]
    )
    # do something else if this already exists
    if len(existing_roles) > 0:
        raise Exception('Emoji already exists on group.')
    
    await orm.execute(
        'INSERT into reaction_role (`guild_id`, `reaction_group_id`, `role_id`, `name`, `emoji`) values (%s, %s, %s, %s, %s)',
        [guild_id, reaction_group_id, role_id, name, emoji]
    )