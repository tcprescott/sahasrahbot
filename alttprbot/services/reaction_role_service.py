"""Reaction-role groups/roles service.

Owns the validation for the (deprecated) reaction-role feature — group/emoji
uniqueness and the per-group role cap — and delegates persistence to the
repository. The cog keeps the deprecation messaging, the
``DISCORD_ROLE_ASSIGNMENT_ENABLED`` gate, and all Discord I/O.
"""

from typing import Any, Dict, List

from alttprbot.exceptions import SahasrahBotException
from alttprbot.repositories import ReactionRoleRepository

MAX_ROLES_PER_GROUP = 20


class ReactionRoleService:
    def __init__(self) -> None:
        self.repository = ReactionRoleRepository()

    async def list_reaction_role_ids(
        self, channel_id: int, message_id: int, emoji: str, guild_id: int
    ) -> List[int]:
        return await self.repository.list_role_ids_by_group_emoji(
            channel_id, message_id, emoji, guild_id
        )

    async def list_guild_groups(self, guild_id: int) -> List[Dict[str, Any]]:
        return await self.repository.list_guild_groups(guild_id)

    async def get_guild_group_by_id(self, group_id: int, guild_id: int) -> List[Dict[str, Any]]:
        return await self.repository.get_guild_group_by_id(group_id, guild_id)

    async def list_group_roles(self, group_id: int, guild_id: int) -> List[Dict[str, Any]]:
        return await self.repository.list_group_roles(group_id, guild_id)

    async def get_role_group(self, role_id: int, guild_id: int) -> List[Dict[str, Any]]:
        return await self.repository.get_role_group(role_id, guild_id)

    async def create_group(
        self, *, guild_id: int, channel_id: int, message_id: int, name: str, description, bot_managed: int
    ) -> None:
        if await self.repository.group_exists_for_message(channel_id, message_id, guild_id):
            raise SahasrahBotException("Group already exists for specified message.")
        await self.repository.create_group(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            name=name,
            description=description,
            bot_managed=bot_managed,
        )

    async def update_group(self, guild_id: int, group_id: int, name: str, description) -> None:
        await self.repository.update_group(guild_id, group_id, name, description)

    async def delete_group(self, guild_id: int, group_id: int) -> None:
        await self.repository.delete_group(guild_id, group_id)

    async def create_role(
        self, *, guild_id: int, reaction_group_id: int, role_id: int, name: str, emoji: str,
        description, protect_mentions: int,
    ) -> None:
        # Order preserves the legacy flow: per-group cap first, then group validity,
        # then emoji uniqueness.
        existing_roles = await self.repository.list_group_roles(reaction_group_id, guild_id)
        if len(existing_roles) >= MAX_ROLES_PER_GROUP:
            raise SahasrahBotException(
                "No more than 20 roles can be on a group.  Please create a new group."
            )
        if not await self.repository.group_exists(reaction_group_id, guild_id):
            raise SahasrahBotException("Invalid group for this guild.")
        if await self.repository.emoji_exists_on_group(emoji, reaction_group_id):
            raise SahasrahBotException("Emoji already exists on group.")
        await self.repository.create_role(
            guild_id=guild_id,
            reaction_group_id=reaction_group_id,
            role_id=role_id,
            name=name,
            emoji=emoji,
            description=description,
            protect_mentions=protect_mentions,
        )

    async def update_role(
        self, guild_id: int, role_id: int, name: str, description, protect_mentions: int
    ) -> None:
        await self.repository.update_role(guild_id, role_id, name, description, protect_mentions)

    async def delete_role(self, guild_id: int, role_id: int) -> None:
        await self.repository.delete_role(guild_id, role_id)
