"""Inquiry message-config service (maps an inquiry message to its target role)."""

from typing import Optional

from alttprbot import models
from alttprbot.repositories import InquiryMessageConfigRepository


class InquiryMessageConfigService:
    def __init__(self) -> None:
        self.repository = InquiryMessageConfigRepository()

    async def get_for_message(self, message_id: int) -> Optional[models.InquiryMessageConfig]:
        return await self.repository.get_by_message_id(message_id)

    async def register(self, *, message_id: int, role_id: int) -> models.InquiryMessageConfig:
        return await self.repository.create(message_id=message_id, role_id=role_id)
