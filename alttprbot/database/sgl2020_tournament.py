from ..util import orm


async def insert_tournament_race(episode_id: int, room_name: str, event: str, permalink=None, seed=None, status=None):
    await orm.execute(
        'INSERT INTO sgl2020_tournament(episode_id, room_name, event, permalink, seed, status) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE room_name = %s, event = %s, permalink = %s, seed = %s, status = %s;',
        [episode_id, room_name, event, permalink, seed, status,
            room_name, event, permalink, seed, status]
    )


async def get_active_tournament_race(room_name: str):
    results = await orm.select(
        'SELECT * from sgl2020_tournament where room_name=%s and status IS NULL;',
        [room_name]
    )
    return results[0] if results else None


async def get_active_tournament_race_by_episodeid(episode_id: str):
    results = await orm.select(
        'SELECT * from sgl2020_tournament where episode_id=%s;',
        [episode_id]
    )
    return results[0] if results else None


async def delete_active_tournament_race(room_name: str):
    await orm.execute(
        'DELETE FROM sgl2020_tournament WHERE room_name=%s and status IS NULL;',
        [room_name]
    )
