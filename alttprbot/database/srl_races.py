from ..util import orm

async def insert_srl_race(srl_id, goal):
    await orm.execute(
        'INSERT INTO srl_races(srl_id, goal) VALUES (%s,%s) ON DUPLICATE KEY UPDATE goal = %s;',
        [srl_id, goal, goal]
    )