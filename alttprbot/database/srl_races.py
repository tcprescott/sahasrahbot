from ..util import orm

async def insert_srl_race(srl_id, goal):
    await orm.execute(
        'INSERT INTO srl_races(srl_id, goal) VALUES (%s,%s) ON DUPLICATE KEY UPDATE goal = %s;',
        [srl_id, goal, goal]
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