from ..util import orm

async def get_categories(guild_id):
    result = await orm.select(
        'SELECT * FROM `discord_server_categories` WHERE guild_id=%s ORDER BY `order` asc, `id` asc;',
        [guild_id]
    )
    return result


async def get_servers_for_category(category_id):
    result = await orm.select(
        'SELECT * FROM `discord_server_lists` WHERE `category_id`=%s ORDER BY `id` asc;',
        [category_id]
    )
    return result