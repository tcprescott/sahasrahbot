"""Data access for the ``audit_messages`` table (message edit/delete logging)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from alttprbot import models


class AuditMessagesRepository:
    @staticmethod
    async def delete_older_than(cutoff: datetime) -> int:
        return await models.AuditMessages.filter(message_date__lte=cutoff).delete()

    @staticmethod
    async def list_by_guild_user_values(
        guild_id: int, user_id: int, limit: int
    ) -> List[Dict[str, Any]]:
        return await models.AuditMessages.filter(
            guild_id=guild_id, user_id=user_id
        ).limit(limit).values()

    @staticmethod
    async def list_deleted_by_guild_user_values(
        guild_id: int, user_id: int, limit: int
    ) -> List[Dict[str, Any]]:
        return await models.AuditMessages.filter(
            guild_id=guild_id, user_id=user_id, deleted=1
        ).limit(limit).values()

    @staticmethod
    async def mark_deleted_by_message_id(message_id: int) -> int:
        return await models.AuditMessages.filter(message_id=message_id).update(deleted=1)

    @staticmethod
    async def list_by_message_id_ordered_values(message_id: int) -> List[Dict[str, Any]]:
        return await models.AuditMessages.filter(message_id=message_id).order_by("id").values()

    @staticmethod
    async def create(
        *,
        guild_id: int,
        message_id: int,
        user_id: int,
        channel_id: int,
        message_date,
        content: Optional[str],
        attachment: Optional[str],
    ) -> models.AuditMessages:
        return await models.AuditMessages.create(
            guild_id=guild_id,
            message_id=message_id,
            user_id=user_id,
            channel_id=channel_id,
            message_date=message_date,
            content=content,
            attachment=attachment,
        )
