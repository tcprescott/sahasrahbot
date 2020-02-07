from ..util import orm

async def insert_message(guild_id: int, message_id: int, user_id: int, channel_id: int, message_date, content):
    await orm.execute(
        'INSERT INTO audit_messages (guild_id, message_id, user_id, channel_id, message_date, content) values (%s, %s, %s, %s, %s, %s)',
        [guild_id, message_id, user_id, channel_id, message_date, content]
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

async def clean_history():
    await orm.execute(
        'DELETE FROM audit_messages WHERE message_date < NOW() - INTERVAL 30 DAY;'
    )