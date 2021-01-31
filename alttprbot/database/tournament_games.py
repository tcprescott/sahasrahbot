import json

from ..util import orm


async def insert_game(episode_id: int, event=None, game_number=None, settings=None, submitted=1):
    await orm.execute(
        'INSERT INTO tournament_games(episode_id, event, game_number, settings, submitted) VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE event = %s, game_number = %s, settings = %s, submitted = %s;',
        [episode_id, event, game_number, json.dumps(settings), submitted,
            game_number, event, json.dumps(settings), submitted]
    )


async def get_game_by_episodeid_submitted(episode_id: str):
    results = await orm.select(
        'SELECT * from tournament_games where episode_id=%s and submitted=1;',
        [episode_id]
    )
    return results[0] if results else None


async def get_game_by_episodeid(episode_id: str):
    results = await orm.select(
        'SELECT * from tournament_games where episode_id=%s;',
        [episode_id]
    )
    return results[0] if results else None


async def get_all_playoffs():
    results = await orm.select(
        'SELECT * from tournament_games where submitted=1;'
    )
    return results
