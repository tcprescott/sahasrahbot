"""Voice roles: members in a mapped voice channel get the mapped role while they are in it.

The ``voice_role`` table. Callers pass ids, never Discord objects.
"""

from typing import List

from alttprbot import models
from alttprbot.services import audit


async def for_guild(guild_id: int) -> List[models.VoiceRole]:
    return await models.VoiceRole.filter(guild_id=guild_id)


async def create(guild_id: int, voice_channel_id: int, role_id: int) -> models.VoiceRole:
    voice_role = await models.VoiceRole.create(guild_id=guild_id, voice_channel_id=voice_channel_id, role_id=role_id)
    await audit.record(audit.VOICE_ROLE_CREATED, target=f'Voice channel {voice_channel_id}', guild_id=guild_id,
                       details={'voice_role_id': voice_role.id, 'voice_channel_id': voice_channel_id,
                                'role_id': role_id})
    return voice_role


async def delete(guild_id: int, voice_role_id: int) -> None:
    deleted = await models.VoiceRole.filter(guild_id=guild_id, id=voice_role_id).delete()
    if deleted:
        await audit.record(audit.VOICE_ROLE_DELETED, target=f'Voice role {voice_role_id}', guild_id=guild_id,
                           details={'voice_role_id': voice_role_id})
