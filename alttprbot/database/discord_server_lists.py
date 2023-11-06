from ..util import orm


async def get_categories(guild_id):
    result = await orm.select(
        'SELECT * FROM `discord_server_categories` WHERE guild_id=%s ORDER BY `order` asc, `id` asc;',
        [guild_id]
    )
    return result


async def get_category(category_id):
    result = await orm.select(
        'SELECT * FROM `discord_server_categories` WHERE id=%s;',
        [category_id]
    )
    return None if result is None else result[0]


async def get_servers_for_category(category_id):
    result = await orm.select(
        'SELECT * FROM `discord_server_lists` WHERE `category_id`=%s ORDER BY `id` asc;',
        [category_id]
    )
    return result


async def get_server(server_id):
    result = await orm.select(
        'SELECT * FROM `discord_server_lists` WHERE `id`=%s;',
        [server_id]
    )
    return None if result is None else result[0]


async def add_server(guild_id, invite_id, category_id, server_description):
    result = await get_category(category_id)
    if not result['guild_id'] == guild_id:
        return

    await orm.execute(
        'INSERT INTO discord_server_lists (`invite_id`, `category_id`, `server_description`) values (%s, %s, %s);',
        [invite_id, category_id, server_description]
    )


async def update_server(guild_id, server_id, invite_id, category_id, server_description):
    result = await get_category(category_id)
    if not result['guild_id'] == guild_id:
        return

    await orm.execute(
        'UPDATE discord_server_lists SET `invite_id`=%s, `category_id`=%s, `server_description`=%s WHERE id=%s;',
        [invite_id, category_id, server_description, server_id]
    )


async def remove_server(guild_id, server_id):
    server_result = await get_server(server_id)
    category_result = await get_category(server_result['category_id'])
    if not category_result['guild_id'] == guild_id:
        return

    await orm.execute(
        'DELETE FROM discord_server_lists WHERE `id`=%s;',
        [server_id]
    )


async def add_category(guild_id, channel_id, category_title, category_description, order=0):
    await orm.execute(
        'INSERT INTO discord_server_categories (guild_id, channel_id, category_title, category_description, `order`) values (%s, %s, %s, %s, %s);',
        [guild_id, channel_id, category_title, category_description, order]
    )


async def update_category(category_id, guild_id, category_title, category_description, order=0):
    await orm.execute(
        'UPDATE discord_server_categories SET category_title=%s, category_description=%s, `order`=%s WHERE id=%s and guild_id=%s;',
        [category_title, category_description, order, category_id, guild_id]
    )


async def remove_category(guild_id, category_id):
    await orm.execute(
        'DELETE FROM discord_server_lists WHERE `id`=%s and `guild_id`=%s;',
        [category_id, guild_id]
    )
