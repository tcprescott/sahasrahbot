"""Application metrics shipped to Sentry Metrics (Explore > Metrics in Sentry).

Where they come from:

* :mod:`alttprbot.observability.runtime` samples the process every
  :data:`SAMPLE_SECONDS` (CPU, memory, event-loop lag, GC, DB pool, the bots).
* :mod:`alttprbot.observability.instrument` counts and times every call into the
  service layer, the external API clients and the seed generators.
* The front ends count and time their own work: web requests
  (``alttprbot_api/telemetry.py``), Discord commands and interactions
  (``alttprbot_discord/telemetry.py``), racetime.gg room commands
  (``alttprbot_racetime/handlers/core.py``), plus scheduled jobs and the event bus.

Every call is a no-op until :func:`alttprbot.observability.sentry.init_sentry`
turns metrics on (a DSN is set and ``SENTRY_METRICS`` isn't off), and none of them
ever raises: a metric is never worth breaking the request or job that produced it.
The attributes each call names are a small, fixed set (a route template, a
command name, a job name), never an id or free text, so charts group cleanly.
Tags set with :func:`~alttprbot.observability.sentry.sentry_tags` (a room, a
guild) ride along as extra attributes for filtering.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from sentry_sdk import metrics as _metrics

SAMPLE_SECONDS = 30.0

_enabled = False


def configure(enabled: bool) -> None:
    global _enabled
    _enabled = enabled


def enabled() -> bool:
    return _enabled


def gauge(name: str, value: Optional[float], unit: Optional[str] = None,
          attributes: Optional[Dict[str, Any]] = None) -> None:
    if not _enabled or value is None:
        return
    try:
        _metrics.gauge(name, value, unit=unit, attributes=attributes)
    except Exception:
        pass


def count(name: str, value: float = 1, unit: Optional[str] = None,
          attributes: Optional[Dict[str, Any]] = None) -> None:
    if not _enabled or not value:
        return
    try:
        _metrics.count(name, value, unit=unit, attributes=attributes)
    except Exception:
        pass


def distribution(name: str, value: Optional[float], unit: Optional[str] = None,
                 attributes: Optional[Dict[str, Any]] = None) -> None:
    if not _enabled or value is None:
        return
    try:
        _metrics.distribution(name, value, unit=unit, attributes=attributes)
    except Exception:
        pass


def outcome_of(exc: Optional[BaseException]) -> str:
    """``ok``, ``rejected`` (a user-facing ``SahasrahBotException``), ``cancelled`` or ``error``."""
    if exc is None:
        return 'ok'
    if isinstance(exc, asyncio.CancelledError):
        return 'cancelled'
    from alttprbot.exceptions import SahasrahBotException
    return 'rejected' if isinstance(exc, SahasrahBotException) else 'error'


def record_call(prefix: str, started: float, exc: Optional[BaseException],
                attributes: Optional[Dict[str, Any]] = None) -> None:
    """Emit ``<prefix>.calls`` and ``<prefix>.duration`` (ms) for one finished call.

    ``started`` is a ``time.perf_counter()`` reading. ``outcome`` is added to the
    attributes.
    """
    if not _enabled:
        return
    attrs = dict(attributes or {})
    attrs['outcome'] = outcome_of(exc)
    count(f'{prefix}.calls', attributes=attrs)
    distribution(f'{prefix}.duration', (time.perf_counter() - started) * 1000,
                 unit='millisecond', attributes=attrs)


@contextmanager
def timed(prefix: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[None]:
    """Time the block and :func:`record_call` it, re-raising whatever it raised."""
    started = time.perf_counter()
    try:
        yield
    except BaseException as e:
        record_call(prefix, started, None if isinstance(e, GeneratorExit) else e, attributes)
        raise
    record_call(prefix, started, None, attributes)
