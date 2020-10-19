import aiocache

from ..util import orm

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)


async def insert_tournament_race(srl_id: str, episode_id: str, event: str, permalink=None, week=None, spoiler=None, status=None):
    key = f'tournament_race_{srl_id}'
    await orm.execute(
        'INSERT INTO tournament_results(srl_id, episode_id, permalink, spoiler, event, week, status) VALUES (%s,%s,%s,%s,%s,%s,%s);',
        [srl_id, episode_id, permalink, spoiler, event, week, status]
    )
    await CACHE.delete(key)

async def update_tournament_results_rolled(srl_id: str, permalink: str, week, status=None):
    key = f'tournament_race_{srl_id}'
    await orm.execute(
        'UPDATE tournament_results SET status=%s, permalink=%s, week=%s where srl_id=%s and status IS NULL;',
        [status, permalink, week, srl_id]
    )
    await CACHE.delete(key)

async def record_tournament_results(srl_id: str, results_json: str):
    key = f'tournament_race_{srl_id}'
    await orm.execute(
        'UPDATE tournament_results SET status="RECORDED", results_json=%s where srl_id=%s and status IS NULL;',
        [results_json, srl_id]
    )
    await CACHE.delete(key)

async def update_tournament_results(srl_id: str, status="STARTED"):
    key = f'tournament_race_{srl_id}'
    await orm.execute(
        'UPDATE tournament_results SET status=%s where srl_id=%s and status IS NULL;',
        [status, srl_id]
    )
    await CACHE.delete(key)

async def get_active_tournament_race(srl_id: str):
    key = f'tournament_race_{srl_id}'
    if await CACHE.exists(key):
        results = await CACHE.get(key)
    else:
        results = await orm.select(
            'SELECT * from tournament_results where srl_id=%s and status IS NULL;',
            [srl_id]
        )
        await CACHE.set(key, results)
    return results[0] if results else None

async def get_active_tournament_race_by_episodeid(episode_id: str):
    results = await orm.select(
        'SELECT * from tournament_results where episode_id=%s;',
        [episode_id]
    )
    return results[0] if results else None

async def delete_active_tournament_race(srl_id: str):
    key = f'tournament_race_{srl_id}'
    await orm.execute(
        'DELETE FROM tournament_results WHERE srl_id=%s and status IS NULL;',
        [srl_id]
    )
    await CACHE.delete(key)
