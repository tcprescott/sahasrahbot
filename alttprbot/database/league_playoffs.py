from ..util import orm
import json

async def insert_playoff(episode_id: int, playoff_round=None, game_number=None, gen_type=None, preset=None, settings=None, submitted=1):
    await orm.execute(
        'INSERT INTO league_playoffs(episode_id, playoff_round, game_number, type, preset, settings, submitted) VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE playoff_round = %s, game_number = %s, type = %s, preset = %s, settings = %s, submitted = %s;',
        [episode_id, playoff_round, game_number, gen_type, preset, json.dumps(settings), submitted,
            playoff_round, game_number, gen_type, preset, json.dumps(settings), submitted]
    )

async def get_playoff_by_episodeid_submitted(episode_id: str):
    results = await orm.select(
        'SELECT * from league_playoffs where episode_id=%s and submitted=1;',
        [episode_id]
    )
    return results[0] if results else None

async def get_playoff_by_episodeid(episode_id: str):
    results = await orm.select(
        'SELECT * from league_playoffs where episode_id=%s;',
        [episode_id]
    )
    return results[0] if results else None

async def get_all_playoffs():
    results = await orm.select(
        'SELECT * from league_playoffs where submitted=1;'
    )
    return results