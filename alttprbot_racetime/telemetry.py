"""Sentry for the racetime.gg bots: every room message tagged, every command traced and timed.

``SahasrahBotCoreHandler`` (``handlers/core.py``) uses these:

* :func:`room_scope` around each message a room receives: any event or log it
  raises is tagged ``racetime_room`` and ``racetime_category``, and
  ``racetime.messages`` counts messages by ``category`` and ``type``.
* :func:`instrument_commands` wraps every ``ex_*`` / ``ex2_*`` chat command
  of a handler class (subclasses get it automatically): its own trace (op
  ``racetime.command``, named ``!seed``), a ``racetime_command`` tag, and
  ``racetime.commands.calls`` / ``racetime.commands.duration`` (ms) by
  ``category``, ``command`` and ``outcome``. A command that raises still raises,
  so racetime-bot reports it in the room as before.
"""

import functools
import inspect
import time
from contextlib import contextmanager
from typing import Any, Iterator

import sentry_sdk

from alttprbot.observability import metrics
from alttprbot.observability.sentry import sentry_tags

_MARK = '__sahasrahbot_racetime_command__'


def category_of(handler: Any) -> str:
    bot = getattr(handler, 'bot', None)
    slug = getattr(bot, 'category_slug', None)
    if slug:
        return slug
    data = getattr(handler, 'data', None) or {}
    return (data.get('category') or {}).get('slug') or 'unknown'


def room_of(handler: Any) -> Any:
    return (getattr(handler, 'data', None) or {}).get('name')


@contextmanager
def room_scope(handler: Any, msg_type: Any) -> Iterator[None]:
    category = category_of(handler)
    metrics.count('racetime.messages', attributes={'category': category, 'type': str(msg_type)})
    with sentry_tags(racetime_room=room_of(handler), racetime_category=category):
        yield


def _command_wrapper(method: str, func):
    command = method.split('_', 1)[1]

    @functools.wraps(func)
    async def instrumented(self, *args, **kwargs):
        category = category_of(self)
        started = time.perf_counter()
        error = None
        with sentry_sdk.isolation_scope(), sentry_tags(
                racetime_room=room_of(self), racetime_category=category, racetime_command=command):
            sentry_sdk.new_trace()
            with sentry_sdk.start_span(name=f'!{command}', attributes={'sentry.op': 'racetime.command'}):
                try:
                    return await func(self, *args, **kwargs)
                except BaseException as e:
                    error = e
                    raise
                finally:
                    metrics.record_call('racetime.commands', started, error,
                                        {'category': category, 'command': command})

    setattr(instrumented, _MARK, True)
    return instrumented


def instrument_commands(cls: type) -> type:
    """Wrap the ``ex_*`` / ``ex2_*`` coroutines ``cls`` defines itself. Returns ``cls``."""
    for name, attr in list(vars(cls).items()):
        if (name.startswith('ex_') or name.startswith('ex2_')) and inspect.iscoroutinefunction(attr) \
                and not getattr(attr, _MARK, False):
            setattr(cls, name, _command_wrapper(name, attr))
    return cls
