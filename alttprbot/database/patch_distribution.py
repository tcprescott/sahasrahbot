from ..util import orm

async def select_random_patch(game):
    result = await orm.select(
        'SELECT * FROM `patch_distribution` WHERE game=%s and `used` is null ORDER BY RAND() LIMIT 1',
        [game]
    )
    return result[0] if result else None

async def update_as_used(record_id):
    await orm.execute(
        'UPDATE patch_distribution SET used=1 where id=%s',
        [record_id]
    )