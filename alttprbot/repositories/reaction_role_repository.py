"""Data access for reaction-role groups and roles.

Backs the (deprecated) reaction-role cog: the ``reaction_group`` / ``reaction_role``
tables. Returns ``.values()`` dicts in the shapes the cog/embeds consume.
"""

from typing import Any, Dict, List

from alttprbot import models

_GROUP_FIELDS = ("id", "guild_id", "channel_id", "message_id", "name", "description", "bot_managed")
_ROLE_FIELDS = (
    "id", "guild_id", "reaction_group_id", "role_id", "name", "emoji", "description", "protect_mentions",
)


class ReactionRoleRepository:
    @staticmethod
    async def list_role_ids_by_group_emoji(
        channel_id: int, message_id: int, emoji: str, guild_id: int
    ) -> List[int]:
        rows = await models.ReactionRole.filter(
            reaction_group__channel_id=channel_id,
            reaction_group__message_id=message_id,
            reaction_group__guild_id=guild_id,
            guild_id=guild_id,
            emoji=emoji,
        ).values("role_id")
        return [row["role_id"] for row in rows]

    @staticmethod
    async def list_guild_groups(guild_id: int) -> List[Dict[str, Any]]:
        return await models.ReactionGroup.filter(guild_id=guild_id).values(*_GROUP_FIELDS)

    @staticmethod
    async def get_guild_group_by_id(reaction_group_id: int, guild_id: int) -> List[Dict[str, Any]]:
        return await models.ReactionGroup.filter(
            id=reaction_group_id, guild_id=guild_id
        ).values(*_GROUP_FIELDS)

    @staticmethod
    async def list_group_roles(reaction_group_id: int, guild_id: int) -> List[Dict[str, Any]]:
        return await models.ReactionRole.filter(
            reaction_group_id=reaction_group_id, guild_id=guild_id
        ).values(*_ROLE_FIELDS)

    @staticmethod
    async def get_role_group(reaction_role_id: int, guild_id: int) -> List[Dict[str, Any]]:
        rows = await models.ReactionRole.filter(
            id=reaction_role_id, guild_id=guild_id
        ).values(
            "reaction_group_id",
            "reaction_group__guild_id",
            "reaction_group__channel_id",
            "reaction_group__message_id",
            "emoji",
        )
        return [
            {
                "id": item["reaction_group_id"],
                "guild_id": item["reaction_group__guild_id"],
                "channel_id": item["reaction_group__channel_id"],
                "message_id": item["reaction_group__message_id"],
                "emoji": item["emoji"],
            }
            for item in rows
        ]

    @staticmethod
    async def group_exists_for_message(channel_id: int, message_id: int, guild_id: int) -> bool:
        return await models.ReactionGroup.filter(
            channel_id=channel_id, message_id=message_id, guild_id=guild_id
        ).exists()

    @staticmethod
    async def group_exists(reaction_group_id: int, guild_id: int) -> bool:
        return await models.ReactionGroup.filter(id=reaction_group_id, guild_id=guild_id).exists()

    @staticmethod
    async def emoji_exists_on_group(emoji: str, reaction_group_id: int) -> bool:
        return await models.ReactionRole.filter(
            emoji=emoji, reaction_group_id=reaction_group_id
        ).exists()

    @staticmethod
    async def create_group(
        *, guild_id: int, channel_id: int, message_id: int, name: str, description, bot_managed: int
    ) -> None:
        await models.ReactionGroup.create(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            name=name,
            description=description,
            bot_managed=bot_managed,
        )

    @staticmethod
    async def update_group(guild_id: int, group_id: int, name: str, description) -> None:
        await models.ReactionGroup.filter(guild_id=guild_id, id=group_id).update(
            name=name, description=description
        )

    @staticmethod
    async def delete_group(guild_id: int, group_id: int) -> None:
        await models.ReactionGroup.filter(guild_id=guild_id, id=group_id).delete()

    @staticmethod
    async def create_role(
        *, guild_id: int, reaction_group_id: int, role_id: int, name: str, emoji: str,
        description, protect_mentions: int,
    ) -> None:
        await models.ReactionRole.create(
            guild_id=guild_id,
            reaction_group_id=reaction_group_id,
            role_id=role_id,
            name=name,
            emoji=emoji,
            description=description,
            protect_mentions=protect_mentions,
        )

    @staticmethod
    async def update_role(
        guild_id: int, role_id: int, name: str, description, protect_mentions: int
    ) -> None:
        await models.ReactionRole.filter(guild_id=guild_id, id=role_id).update(
            name=name, description=description, protect_mentions=protect_mentions
        )

    @staticmethod
    async def delete_role(guild_id: int, role_id: int) -> None:
        await models.ReactionRole.filter(guild_id=guild_id, id=role_id).delete()
