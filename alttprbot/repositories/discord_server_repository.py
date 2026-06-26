"""Data access for the discord server-list tables.

Covers both halves of the one bounded context: ``DiscordServerCategories`` and
the ``DiscordServerLists`` rows they own (reverse relation ``server_list``).
"""

from typing import List, Optional

from alttprbot import models


class DiscordServerRepository:
    # --- categories ---

    @staticmethod
    async def create_category(
        *,
        guild_id: int,
        channel_id: int,
        category_title: str,
        category_description: Optional[str] = None,
        order: int = 0,
    ) -> models.DiscordServerCategories:
        return await models.DiscordServerCategories.create(
            order=order,
            guild_id=guild_id,
            channel_id=channel_id,
            category_title=category_title,
            category_description=category_description,
        )

    @staticmethod
    async def list_categories(guild_id: int) -> List[models.DiscordServerCategories]:
        return await models.DiscordServerCategories.filter(guild_id=guild_id).all()

    @staticmethod
    async def list_categories_with_servers(guild_id: int) -> List[models.DiscordServerCategories]:
        return await models.DiscordServerCategories.filter(guild_id=guild_id).prefetch_related("server_list")

    @staticmethod
    async def delete_category(category_id: int) -> int:
        return await models.DiscordServerCategories.filter(id=category_id).delete()

    @staticmethod
    async def update_category(
        category_id: int,
        *,
        category_title: str,
        category_description: Optional[str],
        order: int = 0,
    ) -> int:
        return await models.DiscordServerCategories.filter(id=category_id).update(
            order=order,
            category_title=category_title,
            category_description=category_description,
        )

    # --- servers ---

    @staticmethod
    async def create_server(
        *,
        invite_id: str,
        category_id: int,
        server_description: str,
    ) -> models.DiscordServerLists:
        return await models.DiscordServerLists.create(
            invite_id=invite_id,
            category_id=category_id,
            server_description=server_description,
        )

    @staticmethod
    async def list_servers(category_id: int) -> List[models.DiscordServerLists]:
        return await models.DiscordServerLists.filter(category_id=category_id)

    @staticmethod
    async def delete_server(server_id: int) -> int:
        return await models.DiscordServerLists.filter(id=server_id).delete()

    @staticmethod
    async def update_server(
        server_id: int,
        *,
        invite_id: str,
        category_id: int,
        server_description: Optional[str] = None,
    ) -> int:
        return await models.DiscordServerLists.filter(id=server_id).update(
            invite_id=invite_id,
            category_id=category_id,
            server_description=server_description,
        )
