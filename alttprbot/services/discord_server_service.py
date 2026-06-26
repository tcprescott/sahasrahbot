"""Discord server-list service.

Business rules for the curated per-guild server directory: validate the admin
inputs and coordinate the repository. Invite resolution (``invite_url`` -> id)
stays in the Discord surface; this service only sees the resolved ``invite_id``.
"""

from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import DiscordServerRepository


class DiscordServerService:
    def __init__(self) -> None:
        self.repository = DiscordServerRepository()

    # --- categories ---

    async def add_category(
        self,
        *,
        guild_id: int,
        channel_id: int,
        category_title: str,
        category_description: Optional[str] = None,
        order: int = 0,
    ) -> models.DiscordServerCategories:
        if not (category_title and category_title.strip()):
            raise ValueError("category_title is required")
        return await self.repository.create_category(
            guild_id=guild_id,
            channel_id=channel_id,
            category_title=category_title,
            category_description=category_description,
            order=order,
        )

    async def list_categories(self, guild_id: int) -> List[models.DiscordServerCategories]:
        return await self.repository.list_categories(guild_id)

    async def list_categories_with_servers(self, guild_id: int) -> List[models.DiscordServerCategories]:
        return await self.repository.list_categories_with_servers(guild_id)

    async def remove_category(self, category_id: int) -> int:
        return await self.repository.delete_category(category_id)

    async def update_category(
        self,
        category_id: int,
        *,
        category_title: str,
        category_description: Optional[str],
        order: int = 0,
    ) -> int:
        if not (category_title and category_title.strip()):
            raise ValueError("category_title is required")
        return await self.repository.update_category(
            category_id,
            category_title=category_title,
            category_description=category_description,
            order=order,
        )

    # --- servers ---

    async def add_server(
        self,
        *,
        invite_id: str,
        category_id: int,
        server_description: str,
    ) -> models.DiscordServerLists:
        if not (server_description and server_description.strip()):
            raise ValueError("server_description is required")
        return await self.repository.create_server(
            invite_id=invite_id,
            category_id=category_id,
            server_description=server_description,
        )

    async def list_servers(self, category_id: int) -> List[models.DiscordServerLists]:
        return await self.repository.list_servers(category_id)

    async def remove_server(self, server_id: int) -> int:
        return await self.repository.delete_server(server_id)

    async def update_server(
        self,
        server_id: int,
        *,
        invite_id: str,
        category_id: int,
        server_description: Optional[str] = None,
    ) -> int:
        return await self.repository.update_server(
            server_id,
            invite_id=invite_id,
            category_id=category_id,
            server_description=server_description,
        )
