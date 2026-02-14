import aiocache

from alttprbot.models import SMZ3Multiworld

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)


async def insert(message_id, owner_id, preset, randomizer, status="STARTED"):
    await SMZ3Multiworld.create(
        message_id=message_id,
        owner_id=owner_id,
        status=status,
        preset=preset,
        randomizer=randomizer
    )


async def update_status(message_id, status):
    key = f'smz3_multiworld_{message_id}'
    await SMZ3Multiworld.filter(message_id=message_id).update(status=status)
    await CACHE.delete(key)


async def fetch(message_id, status="STARTED"):
    key = f'smz3_multiworld_{message_id}'
    if await CACHE.exists(key):
        results = await CACHE.get(key)
    else:
        results = await SMZ3Multiworld.filter(
            message_id=message_id,
            status=status
        ).values('message_id', 'owner_id', 'randomizer', 'preset', 'status')
        await CACHE.set(key, results)
    return results[0] if len(results) > 0 else None
