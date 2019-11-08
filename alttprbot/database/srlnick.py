from ..util import orm

async def insert_srl_nick(discord_user_id, srl_nick):
    await orm.execute(
        'INSERT INTO srlnick(discord_user_id, srl_nick) VALUES (%s,%s) ON DUPLICATE KEY UPDATE srl_nick = %s;',
        [discord_user_id, srl_nick, srl_nick]
    )

async def get_discord_id(srl_nick):
    results = await orm.select(
        'SELECT * from srlnick where srl_nick=%s;',
        [srl_nick]
    )
    return results if len(results) > 0 else False

async def get_srl_nick(discord_user_id):
    results = await orm.select(
        'SELECT * from srlnick where discord_user_id=%s;',
        [discord_user_id]
    )
    return results if len(results) > 0 else False