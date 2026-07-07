"""Message-audit service (the audit bot's message edit/delete log).

Distinct from AuditService (generated-game / async-race audit). Backs the audit
cog's message history, deletion marking, and retention cleanup.
"""

import datetime
from typing import Any, Dict, List, Optional

from alttprbot import models
from alttprbot.repositories import AuditMessagesRepository


class AuditMessagesService:
    def __init__(self) -> None:
        self.repository = AuditMessagesRepository()

    async def clean_old_messages(self, days: int = 30) -> int:
        cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=days)
        return await self.repository.delete_older_than(cutoff)

    async def list_user_history(self, guild_id: int, user_id: int, limit: int) -> List[Dict[str, Any]]:
        return await self.repository.list_by_guild_user_values(guild_id, user_id, limit)

    async def list_deleted_user_history(self, guild_id: int, user_id: int, limit: int) -> List[Dict[str, Any]]:
        return await self.repository.list_deleted_by_guild_user_values(guild_id, user_id, limit)

    async def mark_deleted(self, message_id: int) -> int:
        return await self.repository.mark_deleted_by_message_id(message_id)

    async def get_message_history(self, message_id: int) -> List[Dict[str, Any]]:
        return await self.repository.list_by_message_id_ordered_values(message_id)

    async def record_message(
        self,
        *,
        guild_id: int,
        message_id: int,
        user_id: int,
        channel_id: int,
        message_date,
        content: Optional[str],
        attachment: Optional[str],
    ) -> models.AuditMessages:
        return await self.repository.create(
            guild_id=guild_id,
            message_id=message_id,
            user_id=user_id,
            channel_id=channel_id,
            message_date=message_date,
            content=content,
            attachment=attachment,
        )
