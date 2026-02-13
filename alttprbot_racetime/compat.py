from dataclasses import dataclass


@dataclass
class HandlerTask:
    task: object
    handler: object


def get_room_handler(bot, room_name):
    entry = bot.handlers.get(room_name)
    if entry is None:
        return None
    return getattr(entry, 'handler', entry)
