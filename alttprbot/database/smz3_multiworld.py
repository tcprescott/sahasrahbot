import aiocache

from ..util import orm

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)


async def insert(message_id, owner_id, preset, randomizer, status="STARTED"):
    await orm.execute(
        'INSERT INTO smz3_multiworld(message_id, owner_id, status, preset, randomizer) VALUES (%s,%s,%s,%s,%s);',
        [message_id, owner_id, status, preset, randomizer]
    )


async def update_status(message_id, status):
    key = f'smz3_multiworld_{message_id}'
    await orm.execute(
        'UPDATE smz3_multiworld SET status=%s WHERE message_id=%s;',
        [status, message_id]
    )
    await CACHE.delete(key)


async def fetch(message_id, status="STARTED"):
    key = f'smz3_multiworld_{message_id}'
    if await CACHE.exists(key):
        results = await CACHE.get(key)
    else:
        results = await orm.select(
            'SELECT * from smz3_multiworld WHERE message_id=%s and status=%s;',
            [message_id, status]
        )
        await CACHE.set(key, results)
    return results[0] if len(results) > 0 else None
