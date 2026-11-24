"""In-process event bus: services publish, notifiers subscribe.

Domain and service code calls :func:`publish` after something has happened (a
race room opened, a ballot was cast). Subscribers, registered at startup, turn
that into a Discord post, a DM or anything else. The publisher never learns who
is listening, so it doesn't need to import the Discord bot.

The contract, borrowed from Wizzrobe's bus:

* ``publish`` is a plain synchronous call. It never awaits, never blocks and
  never raises: each matching subscriber runs as its own task on the running
  loop, and a subscriber's exception is logged (and so reaches Sentry) without
  touching the publisher or the other subscribers.
* Subscribers are ``async def handler(event)`` coroutines. They do the I/O, so a
  slow Discord call can't hold up a racetime handler.
* Delivery is best effort and in-process only. Nothing is persisted: an event
  published while no loop is running, or with no subscriber, is dropped.

This module imports nothing from the Discord, racetime or web packages, so any
layer can publish.

Sentry: ``events.published`` counts each event by ``event``; every delivery emits
``event.calls`` / ``event.duration`` with ``event``, ``subscriber`` and ``outcome``,
is a child span of whatever published it (when that is traced), and tags a
failure with the event and subscriber. ``pending_count()`` feeds the
``events.pending`` gauge.
"""

import asyncio
import itertools
import logging
import time
from typing import Awaitable, Callable, Iterable, Type, Union

import sentry_sdk

from alttprbot.events.event import Event
from alttprbot.observability import metrics
from alttprbot.observability.sentry import sentry_tags

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None]]
EventClasses = Union[Type[Event], Iterable[Type[Event]]]

_subscribers: dict[int, tuple[tuple[Type[Event], ...], Handler]] = {}
_tokens = itertools.count(1)
_pending: set[asyncio.Task] = set()


def subscribe(event_classes: EventClasses, handler: Handler) -> int:
    """Run ``handler`` for every published event of the given class(es).

    Subclasses match too, so subscribing to :class:`Event` receives everything.
    Returns a token for :func:`unsubscribe`.
    """
    if isinstance(event_classes, type):
        event_classes = (event_classes,)
    classes = tuple(event_classes)
    if not classes or not all(isinstance(c, type) and issubclass(c, Event) for c in classes):
        raise TypeError(f"subscribe() needs Event subclasses, got {event_classes!r}")
    if not asyncio.iscoroutinefunction(handler):
        raise TypeError(f"subscriber {handler!r} must be an async function")

    token = next(_tokens)
    _subscribers[token] = (classes, handler)
    return token


def unsubscribe(token: int) -> None:
    """Remove a subscriber. Unknown tokens are ignored."""
    _subscribers.pop(token, None)


def publish(event: Event) -> None:
    """Hand ``event`` to every matching subscriber. Never raises, never blocks."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("Dropped %s: published with no running event loop", event.name)
        return
    metrics.count('events.published', attributes={'event': event.name})

    for classes, handler in _subscribers.values():
        if not isinstance(event, classes):
            continue
        try:
            task = loop.create_task(_deliver(handler, event), name=f"event:{event.name}")
        except Exception:
            logger.exception("Could not schedule subscriber %r for %s", handler, event.name)
            continue
        _pending.add(task)
        task.add_done_callback(_pending.discard)


def _subscriber_name(handler: Handler) -> str:
    return str(getattr(handler, "__qualname__", None) or getattr(handler, "__name__", None) or handler)


async def _deliver(handler: Handler, event: Event) -> None:
    subscriber = _subscriber_name(handler)
    started = time.perf_counter()
    error = None
    with sentry_tags(event=event.name, event_subscriber=subscriber):
        try:
            if sentry_sdk.get_current_span() is None:
                await handler(event)
            else:
                with sentry_sdk.start_span(name=f"{event.name} -> {subscriber}", attributes={'sentry.op': 'event'}):
                    await handler(event)
        except Exception as e:
            error = e
            logger.exception("Event subscriber %s failed for %s", subscriber, event)
        except asyncio.CancelledError as e:
            error = e
            raise
        finally:
            metrics.record_call('event', started, error, {'event': event.name, 'subscriber': subscriber})


def pending_count() -> int:
    """Deliveries scheduled and not yet finished."""
    return len(_pending)


async def drain() -> None:
    """Wait until every subscriber scheduled so far has finished. For tests."""
    while _pending:
        await asyncio.gather(*list(_pending), return_exceptions=True)


def clear() -> None:
    """Forget every subscriber. For tests."""
    _subscribers.clear()
