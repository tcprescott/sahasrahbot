"""Data access for the ``inquiry_message_config`` table."""

from typing import Optional

from alttprbot import models


class InquiryMessageConfigRepository:
    @staticmethod
    async def get_by_message_id(message_id: int) -> Optional[models.InquiryMessageConfig]:
        return await models.InquiryMessageConfig.get_or_none(message_id=message_id)

    @staticmethod
    async def create(*, message_id: int, role_id: int) -> models.InquiryMessageConfig:
        return await models.InquiryMessageConfig.create(message_id=message_id, role_id=role_id)
