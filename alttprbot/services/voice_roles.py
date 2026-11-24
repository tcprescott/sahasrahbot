"""Voice roles: members in a mapped voice channel get the mapped role while they are in it.

The ``voice_role`` table. Callers pass ids, never Discord objects.
"""

from typing import List

from alttprbot import models


async def for_guild(guild_id: int) -> List[models.VoiceRole]:
    return await models.VoiceRole.filter(guild_id=guild_id)


async def create(guild_id: int, voice_channel_id: int, role_id: int) -> models.VoiceRole:
    return await models.VoiceRole.create(guild_id=guild_id, voice_channel_id=voice_channel_id, role_id=role_id)


async def delete(guild_id: int, voice_role_id: int) -> None:
    await models.VoiceRole.filter(guild_id=guild_id, id=voice_role_id).delete()
