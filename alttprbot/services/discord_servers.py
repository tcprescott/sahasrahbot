"""The Discord server list: categories of partner servers that a guild posts to its channels.

Each category belongs to a guild and is posted to one channel; each server in it is a
Discord invite code plus a description. ``/discordservers refresh`` reposts every
category, ten servers per message.

Callers pass ids and plain values, never Discord objects.
"""

from dataclasses import dataclass
from typing import List, Optional

from alttprbot import models
from alttprbot.services import audit

SERVERS_PER_MESSAGE = 10


@dataclass(frozen=True)
class ServerListPage:
    """One message of a category's server list."""
    channel_id: int
    category_title: str
    part: int  # 1-based
    part_count: int
    servers: List[models.DiscordServerLists]


@dataclass(frozen=True)
class ServerListLayout:
    """Everything ``refresh`` posts: the channels to clear, then the pages to send, in order."""
    channel_ids: List[int]
    pages: List[ServerListPage]


async def add_category(guild_id: int, channel_id: int, category_title: str,
                       category_description: Optional[str] = None, order: int = 0) -> models.DiscordServerCategories:
    category = await models.DiscordServerCategories.create(
        order=order,
        guild_id=guild_id,
        channel_id=channel_id,
        category_title=category_title,
        category_description=category_description
    )
    await audit.record(audit.SERVER_LIST_CATEGORY_ADDED, target=category_title, guild_id=guild_id,
                       details={'category_id': category.id, 'channel_id': channel_id})
    return category


async def list_categories(guild_id: int) -> List[models.DiscordServerCategories]:
    return await models.DiscordServerCategories.filter(guild_id=guild_id).all()


async def remove_category(category_id: int) -> None:
    category = await models.DiscordServerCategories.get_or_none(id=category_id)
    await models.DiscordServerCategories.filter(id=category_id).delete()
    if category is not None:
        await audit.record(audit.SERVER_LIST_CATEGORY_REMOVED, target=category.category_title,
                           guild_id=category.guild_id, details={'category_id': category_id})


async def update_category(category_id: int, category_title: str, category_description: Optional[str],
                          order: int = 0) -> None:
    before = await models.DiscordServerCategories.get_or_none(id=category_id)
    await models.DiscordServerCategories.filter(id=category_id).update(
        order=order,
        category_title=category_title,
        category_description=category_description
    )
    if before is not None:
        changed = audit.changes(
            {'title': before.category_title, 'description': before.category_description, 'order': before.order},
            {'title': category_title, 'description': category_description, 'order': order})
        await audit.record(audit.SERVER_LIST_CATEGORY_UPDATED, target=category_title, guild_id=before.guild_id,
                           details={'category_id': category_id, 'changes': changed})


async def add_server(guild_id: int, category_id: int, invite_id: str,
                     server_description: str) -> models.DiscordServerLists:
    # DiscordServerLists has no guild_id column; Tortoise ignores the keyword. Kept as it was.
    server = await models.DiscordServerLists.create(
        guild_id=guild_id,
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description
    )
    await audit.record(audit.SERVER_LIST_SERVER_ADDED, target=server_description or invite_id, guild_id=guild_id,
                       details={'server_id': server.id, 'category_id': category_id, 'invite_id': invite_id})
    return server


async def list_servers(category_id: int) -> List[models.DiscordServerLists]:
    return await models.DiscordServerLists.filter(category_id=category_id)


async def _category_guild(category_id: Optional[int]) -> Optional[int]:
    category = await models.DiscordServerCategories.get_or_none(id=category_id) if category_id else None
    return category.guild_id if category else None


async def remove_server(server_id: int) -> None:
    server = await models.DiscordServerLists.get_or_none(id=server_id)
    await models.DiscordServerLists.filter(id=server_id).delete()
    if server is not None:
        await audit.record(audit.SERVER_LIST_SERVER_REMOVED, target=server.server_description or server.invite_id,
                           guild_id=await _category_guild(server.category_id),
                           details={'server_id': server_id, 'invite_id': server.invite_id})


async def update_server(server_id: int, invite_id: str, category_id: int,
                        server_description: Optional[str] = None) -> None:
    before = await models.DiscordServerLists.get_or_none(id=server_id)
    await models.DiscordServerLists.filter(id=server_id).update(
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description
    )
    if before is not None:
        changed = audit.changes(
            {'invite_id': before.invite_id, 'category_id': before.category_id,
             'description': before.server_description},
            {'invite_id': invite_id, 'category_id': category_id, 'description': server_description})
        await audit.record(audit.SERVER_LIST_SERVER_UPDATED, target=server_description or invite_id,
                           guild_id=await _category_guild(category_id),
                           details={'server_id': server_id, 'changes': changed})


async def server_list_layout(guild_id: int) -> ServerListLayout:
    """The guild's server list split into messages of ``SERVERS_PER_MESSAGE`` servers.

    Every category's channel is listed in ``channel_ids`` once, even when the category
    has no servers (it is still cleared). A category with no servers gets no page.
    """
    categories = await models.DiscordServerCategories.filter(guild_id=guild_id).prefetch_related('server_list')
    channel_ids = list({c.channel_id for c in categories})

    pages = []
    for category in categories:
        server_list: List[models.DiscordServerLists] = list(category.server_list)
        chunks = [server_list[i:i + SERVERS_PER_MESSAGE]
                  for i in range(0, len(server_list), SERVERS_PER_MESSAGE)]
        for idx, servers in enumerate(chunks):
            pages.append(ServerListPage(
                channel_id=category.channel_id,
                category_title=category.category_title,
                part=idx + 1,
                part_count=len(chunks),
                servers=servers,
            ))

    return ServerListLayout(channel_ids=channel_ids, pages=pages)
