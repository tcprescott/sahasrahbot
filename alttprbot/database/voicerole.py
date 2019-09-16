from ..util import orm


async def get_voice_roles_by_guild(guild_id):
    result = await orm.select(
        'SELECT guild_id, voice_channel_id, role_id FROM voice_role WHERE guild_id=%s;',
        [guild_id]
    )
    return result


async def create_voice_role(guild_id, voice_channel_id, role_id):
    await orm.execute(
        'INSERT INTO voice_role (guild_id, voice_channel_id, role_id) values (%s, %s, %s);',
        [guild_id, voice_channel_id, role_id]
    )


async def delete_voice_role(guild_id, id):
    await orm.execute(
        'DELETE FROM voice_role WHERE guild_id=%s AND id=%s;',
        [guild_id, id]
    )
