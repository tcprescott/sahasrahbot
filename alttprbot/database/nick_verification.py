from ..util import orm

async def insert_verification(key, discord_user_id):
    await orm.execute(
        'INSERT INTO nick_verification(`key`, `discord_user_id`) VALUES (%s, %s);',
        [key, discord_user_id]
    )


async def get_verification(key):
    results = await orm.select(
        'SELECT * from nick_verification where `key`=%s;',
        [key]
    )
    return results[0] if len(results) > 0 else None


async def delete_verification(key):
    await orm.execute(
        'DELETE FROM nick_verification WHERE `key`=%s',
        [key]
    )
