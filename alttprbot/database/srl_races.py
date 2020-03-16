from ..util import orm

async def insert_srl_race(srl_id, goal, message=None):
    await orm.execute(
        'INSERT INTO srl_races(srl_id, goal, message) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE goal = %s, message = %s;',
        [srl_id, goal, message, goal, message]
    )

async def delete_srl_race(srl_id):
    await orm.execute(
        'DELETE FROM srl_races WHERE srl_id=%s;',
        [srl_id]
    )


async def get_srl_races():
    results = await orm.select(
        'SELECT * from srl_races;'
    )
    return results

async def get_srl_race_by_id(srl_id):
    results = await orm.select(
        'SELECT * from srl_races where srl_id=%s;',
        [srl_id]
    )
    return results[0] if len(results) > 0 else False