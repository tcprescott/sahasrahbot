from ..util import orm


async def insert_spoiler_race(srl_id, spoiler_url, studytime=900):
    await orm.execute(
        'INSERT INTO spoiler_races(srl_id, spoiler_url, studytime) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE spoiler_url = %s, studytime = %s, started = null;',
        [srl_id, spoiler_url, studytime, spoiler_url, studytime]
    )

async def start_spoiler_race(srl_id):
    await orm.execute(
        'UPDATE spoiler_races SET started=CURRENT_TIMESTAMP() where srl_id=%s',
        [srl_id]
    )

async def delete_spoiler_race(srl_id):
    await orm.execute(
        'DELETE FROM spoiler_races WHERE srl_id=%s;',
        [srl_id]
    )


async def get_spoiler_races():
    results = await orm.select(
        'SELECT * from spoiler_races;'
    )
    return results


async def get_spoiler_race_by_id(srl_id):
    results = await orm.select(
        'SELECT * from spoiler_races where srl_id=%s and started is null;',
        [srl_id]
    )
    return results[0] if len(results) > 0 else False

async def get_spoiler_race_by_id_started(srl_id):
    results = await orm.select(
        'SELECT * from spoiler_races where srl_id=%s and CURRENT_TIMESTAMP() <= TIMESTAMPADD(SECOND,studytime,started);',
        [srl_id]
    )
    return results[0] if len(results) > 0 else False
