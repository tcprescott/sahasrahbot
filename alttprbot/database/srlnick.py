from ..util import orm


async def insert_srl_nick(discord_user_id, srl_nick, srl_verified: int = 0):
    await orm.execute(
        'INSERT INTO srlnick(`discord_user_id`, `srl_nick`, `srl_verified`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE `srl_nick` = %s, `srl_verified` = %s;',
        [discord_user_id, srl_nick, srl_verified, srl_nick, srl_verified]
    )


async def insert_twitch_name(discord_user_id, twitch_name):
    await orm.execute(
        'INSERT INTO srlnick(discord_user_id, twitch_name) VALUES (%s,%s) ON DUPLICATE KEY UPDATE twitch_name = %s;',
        [discord_user_id, twitch_name, twitch_name]
    )


async def insert_rtgg_id(discord_user_id, rtgg_id):
    await orm.execute(
        'INSERT INTO srlnick(discord_user_id, rtgg_id) VALUES (%s,%s) ON DUPLICATE KEY UPDATE rtgg_id = %s;',
        [discord_user_id, rtgg_id, rtgg_id]
    )


async def get_discord_id(srl_nick):
    results = await orm.select(
        'SELECT * from srlnick where srl_nick=%s;',
        [srl_nick]
    )
    return results if len(results) > 0 else False


async def get_discord_id_by_twitch(twitch_name):
    results = await orm.select(
        'SELECT * from srlnick where twitch_name=%s;',
        [twitch_name]
    )
    return results if len(results) > 0 else False


async def get_discord_id_by_rtgg(rtgg_id):
    results = await orm.select(
        'SELECT * from srlnick where rtgg_id=%s;',
        [rtgg_id]
    )
    return results if len(results) > 0 else False


async def get_nickname(discord_user_id):
    results = await orm.select(
        'SELECT * from srlnick where discord_user_id=%s;',
        [discord_user_id]
    )
    return results[0] if results else None
