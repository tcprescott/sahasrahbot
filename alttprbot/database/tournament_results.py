from ..util import orm

async def insert_tournament_race(srl_id: str, episode_id: str, permalink: str, event: str, week: str, spoiler=None):
    await orm.execute(
        'INSERT INTO tournament_results(srl_id, episode_id, permalink, spoiler, event, week) VALUES (%s,%s,%s,%s,%s,%s);',
        [srl_id, episode_id, permalink, spoiler, event, week]
    )

async def record_tournament_results(srl_id: str, results_json: str):
    await orm.execute(
        'UPDATE tournament_results SET status="RECORDED", results_json=%s where srl_id=%s and status IS NULL;',
        [results_json, srl_id]
    )

async def get_active_tournament_race(srl_id: str):
    results = await orm.select(
        'SELECT * from tournament_results where srl_id=%s and status IS NULL;',
        [srl_id]
    )
    return results[0] if results else None

async def delete_active_touranment_race(srl_id: str):
    await orm.execute(
        'DELETE FROM tournament_results WHERE srl_id=%s and status IS NULL;',
        [srl_id]
    )
