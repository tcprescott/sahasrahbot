from ..util import orm


async def insert_tournament_race(episode_id: int, room_name: str, event: str, platform: str, permalink=None, seed=None,
                                 password=None, status=None):
    await orm.execute(
        'INSERT INTO sgl2020_tournament(episode_id, room_name, event, platform, permalink, seed, password, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE room_name = %s, event = %s, platform = %s, permalink = %s, seed = %s, password = %s, status = %s;',
        [episode_id, room_name, event, platform, permalink, seed, password, status,
         room_name, event, platform, permalink, seed, password, status]
    )


async def update_tournament_race_status(room_name: int, status="STARTED"):
    await orm.execute(
        'UPDATE sgl2020_tournament SET status = %s WHERE room_name = %s', [
            status, room_name]
    )


async def get_active_tournament_race(room_name: str):
    results = await orm.select(
        'SELECT * from sgl2020_tournament where room_name=%s and status IS NULL;',
        [room_name]
    )
    return results[0] if results else None


async def get_tournament_race_by_episodeid(episode_id: str):
    results = await orm.select(
        'SELECT * from sgl2020_tournament where episode_id=%s;',
        [episode_id]
    )
    return results[0] if results else None


async def get_all_tournament_races():
    results = await orm.select(
        'SELECT * from sgl2020_tournament;'
    )
    return results


async def get_unrecorded_races():
    results = await orm.select(
        'SELECT * from sgl2020_tournament where (`status` is null or `status` = "STARTED") and platform = "racetime";'
    )
    return results


async def delete_active_tournament_race(room_name: str):
    await orm.execute(
        'DELETE FROM sgl2020_tournament WHERE room_name=%s and status IS NULL;',
        [room_name]
    )
