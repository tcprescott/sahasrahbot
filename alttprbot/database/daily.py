from ..util import orm


async def get_latest_daily():
    result = await orm.select(
        'SELECT hash FROM daily ORDER BY id DESC LIMIT 1;',
        []
    )
    return result[0]


async def set_new_daily(hash_id):
    await orm.execute(
        'INSERT INTO daily (`hash`) values (%s)',
        [hash_id]
    )
