from ..util import orm

async def insert_command_text(channel, command, content):
    await orm.execute(
        'INSERT INTO twitch_command_text(`channel`, `command`, `content`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE `content` = %s;',
        [channel, command, content, content]
    )

async def get_command_text(channel, command):
    results = await orm.select(
        'SELECT * from twitch_command_text where channel=%s and command=%s;',
        [channel, command]
    )
    return results[0] if len(results) > 0 else None