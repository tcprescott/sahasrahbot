from alttprbot.models import DiscordServerCategories, DiscordServerLists


async def get_categories(guild_id):
    result = await DiscordServerCategories.filter(
        guild_id=guild_id
    ).order_by('order', 'id').values(
        'id', 'order', 'guild_id', 'channel_id', 'category_title', 'category_description'
    )
    return result


async def get_category(category_id):
    result = await DiscordServerCategories.filter(
        id=category_id
    ).values(
        'id', 'order', 'guild_id', 'channel_id', 'category_title', 'category_description'
    )
    return result[0] if result else None


async def get_servers_for_category(category_id):
    result = await DiscordServerLists.filter(
        category_id=category_id
    ).order_by('id').values('id', 'server_description', 'invite_id', 'category_id')
    return result


async def get_server(server_id):
    result = await DiscordServerLists.filter(
        id=server_id
    ).values('id', 'server_description', 'invite_id', 'category_id')
    return result[0] if result else None


async def add_server(guild_id, invite_id, category_id, server_description):
    result = await get_category(category_id)
    if result is None or result['guild_id'] != guild_id:
        return

    await DiscordServerLists.create(
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description
    )


async def update_server(guild_id, server_id, invite_id, category_id, server_description):
    result = await get_category(category_id)
    if result is None or result['guild_id'] != guild_id:
        return

    await DiscordServerLists.filter(id=server_id).update(
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description
    )


async def remove_server(guild_id, server_id):
    server_result = await get_server(server_id)
    if server_result is None:
        return

    category_result = await get_category(server_result['category_id'])
    if category_result is None or category_result['guild_id'] != guild_id:
        return

    await DiscordServerLists.filter(id=server_id).delete()


async def add_category(guild_id, channel_id, category_title, category_description, order=0):
    await DiscordServerCategories.create(
        guild_id=guild_id,
        channel_id=channel_id,
        category_title=category_title,
        category_description=category_description,
        order=order
    )


async def update_category(category_id, guild_id, category_title, category_description, order=0):
    await DiscordServerCategories.filter(id=category_id, guild_id=guild_id).update(
        category_title=category_title,
        category_description=category_description,
        order=order
    )


async def remove_category(guild_id, category_id):
    category = await DiscordServerCategories.filter(
        id=category_id,
        guild_id=guild_id
    ).exists()
    if not category:
        return

    await DiscordServerLists.filter(category_id=category_id).delete()
    await DiscordServerCategories.filter(id=category_id, guild_id=guild_id).delete()
