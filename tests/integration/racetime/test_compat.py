"""Tests for the racetime room-handler lookup helper.

See alttprbot/presentation/racetime/compat.py.
"""

from types import SimpleNamespace

from alttprbot.presentation.racetime.compat import HandlerTask, get_room_handler


def test_handler_task_holds_fields():
    sentinel_task = object()
    sentinel_handler = object()
    entry = HandlerTask(task=sentinel_task, handler=sentinel_handler)
    assert entry.task is sentinel_task
    assert entry.handler is sentinel_handler


def test_get_room_handler_missing_room_returns_none():
    bot = SimpleNamespace(handlers={})
    assert get_room_handler(bot, "alttpr/none") is None


def test_get_room_handler_unwraps_handler_task():
    handler = object()
    bot = SimpleNamespace(handlers={"alttpr/r1": HandlerTask(task=None, handler=handler)})
    assert get_room_handler(bot, "alttpr/r1") is handler


def test_get_room_handler_returns_entry_without_handler_attr():
    # An entry that is not a HandlerTask (no .handler attribute) is returned as-is.
    entry = SimpleNamespace(something="else")
    bot = SimpleNamespace(handlers={"alttpr/r2": entry})
    assert get_room_handler(bot, "alttpr/r2") is entry
