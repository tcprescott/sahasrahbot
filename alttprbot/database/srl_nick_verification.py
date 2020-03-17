from ..util import orm

async def insert_verification(srl_nick, key, discord_user_id):
    await orm.execute(
        'INSERT INTO srl_nick_verification(`srl_nick`, `key`, `discord_user_id`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE `srl_nick` = %s, `key` = %s, `discord_user_id` = %s;',
        [srl_nick, key, discord_user_id, srl_nick, key, discord_user_id]
    )

async def get_verification(srl_nick, key):
    results = await orm.select(
        'SELECT * from srl_nick_verification where `srl_nick`=%s AND `key`=%s;',
        [srl_nick, key]
    )
    return results[0] if len(results) > 0 else None

async def delete_verification(srl_nick):
    await orm.execute(
        'DELETE FROM srl_nick_verification WHERE `srl_nick`=%s',
        [srl_nick]
    )