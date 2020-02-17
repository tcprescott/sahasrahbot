import json

from ..util import orm

async def insert_message(guild_id: int, message_id: int, user_id: int, channel_id: int, message_date, content, attachment):
    await orm.execute(
        'INSERT INTO audit_messages (guild_id, message_id, user_id, channel_id, message_date, content, attachment) values (%s, %s, %s, %s, %s, %s, %s)',
        [guild_id, message_id, user_id, channel_id, message_date, content, attachment]
    )

async def get_cached_messages(message_id: int):
    result = await orm.select(
        'SELECT * from audit_messages WHERE message_id=%s order by id asc;',
        [message_id]
    )
    return result

async def set_deleted(message_id: int):
    await orm.execute(
        'UPDATE audit_messages SET deleted=1 WHERE message_id=%s',
        [message_id]
    )

async def insert_generated_game(randomizer, hash_id, permalink, settings, gentype, genoption):
    await orm.execute(
        'INSERT INTO audit_generated_games (randomizer, hash_id, permalink, settings, gentype, genoption) values (%s, %s, %s, %s, %s, %s)',
        [randomizer, hash_id, permalink, json.dumps(settings), gentype, genoption]
    )

async def get_generated_game(hash_id):
    results = await orm.select(
        'SELECT * from audit_generated_games WHERE hash_id=%s;',
        [hash_id]
    )
    return results[0] if len(results) > 0 else None