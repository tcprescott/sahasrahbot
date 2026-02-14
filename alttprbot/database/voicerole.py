from alttprbot.models import VoiceRole


async def get_voice_roles_by_guild(guild_id):
    result = await VoiceRole.filter(
        guild_id=guild_id
    ).values('guild_id', 'voice_channel_id', 'role_id')
    return result


async def create_voice_role(guild_id, voice_channel_id, role_id):
    await VoiceRole.create(
        guild_id=guild_id,
        voice_channel_id=voice_channel_id,
        role_id=role_id
    )


async def delete_voice_role(guild_id, role_id):
    await VoiceRole.filter(
        guild_id=guild_id,
        id=role_id
    ).delete()
