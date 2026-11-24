"""The Discord server list: categories of partner servers that a guild posts to its channels.

Each category belongs to a guild and is posted to one channel; each server in it is a
Discord invite code plus a description. ``/discordservers refresh`` reposts every
category, ten servers per message.

Callers pass ids and plain values, never Discord objects.
"""

from dataclasses import dataclass
from typing import List, Optional

from alttprbot import models

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
    return await models.DiscordServerCategories.create(
        order=order,
        guild_id=guild_id,
        channel_id=channel_id,
        category_title=category_title,
        category_description=category_description
    )


async def list_categories(guild_id: int) -> List[models.DiscordServerCategories]:
    return await models.DiscordServerCategories.filter(guild_id=guild_id).all()


async def remove_category(category_id: int) -> None:
    await models.DiscordServerCategories.filter(id=category_id).delete()


async def update_category(category_id: int, category_title: str, category_description: Optional[str],
                          order: int = 0) -> None:
    await models.DiscordServerCategories.filter(id=category_id).update(
        order=order,
        category_title=category_title,
        category_description=category_description
    )


async def add_server(guild_id: int, category_id: int, invite_id: str,
                     server_description: str) -> models.DiscordServerLists:
    # DiscordServerLists has no guild_id column; Tortoise ignores the keyword. Kept as it was.
    return await models.DiscordServerLists.create(
        guild_id=guild_id,
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description
    )


async def list_servers(category_id: int) -> List[models.DiscordServerLists]:
    return await models.DiscordServerLists.filter(category_id=category_id)


async def remove_server(server_id: int) -> None:
    await models.DiscordServerLists.filter(id=server_id).delete()


async def update_server(server_id: int, invite_id: str, category_id: int,
                        server_description: Optional[str] = None) -> None:
    await models.DiscordServerLists.filter(id=server_id).update(
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description
    )


async def server_list_layout(guild_id: int) -> ServerListLayout:
    """The guild's server list split into messages of ``SERVERS_PER_MESSAGE`` servers.

    Every category's channel is listed in ``channel_ids`` once, even when the category
    has no servers (it is still cleared). A category with no servers gets no page.
    """
    categories = await models.DiscordServerCategories.filter(guild_id=guild_id).prefetch_related('server_list')
    channel_ids = list(set([c.channel_id for c in categories]))

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
