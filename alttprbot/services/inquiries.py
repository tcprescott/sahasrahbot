"""Inquiry messages: a Discord message with a button that opens a private thread for a
role. This module remembers which role each message is for."""

from typing import Optional

from alttprbot import models
from alttprbot.services import audit


async def register(message_id: int, role_id: int, guild_id: Optional[int] = None) -> None:
    await models.InquiryMessageConfig.create(message_id=message_id, role_id=role_id)
    await audit.record(audit.INQUIRY_CREATED, target=f'Message {message_id}', guild_id=guild_id,
                       details={'message_id': message_id, 'role_id': role_id})


async def role_for_message(message_id: int) -> int:
    """The role an inquiry message opens threads for. Raises ``DoesNotExist`` for a
    message that isn't one, as the button always has."""
    config = await models.InquiryMessageConfig.get(message_id=message_id)
    return config.role_id
