"""Process and bot load, sampled to Sentry Metrics every 30 seconds.

Modelled on Wizzrobe's ``metrics_sampler``: the figures that explain "it was slow
on Saturday afternoon" after the fact. :func:`start` is called once the loop is
running (``sahasrahbot.py``), and only when metrics are on.

Gauges every :data:`~alttprbot.observability.metrics.SAMPLE_SECONDS`:

* ``process.cpu`` (percent, 100 = one core), ``process.memory_rss`` (MB),
  ``process.asyncio_tasks``, ``process.threads``
* ``loop.lag_p50`` / ``loop.lag_p95`` / ``loop.lag_max`` (ms) over the last
  sample, from a heartbeat four times a second; ``loop.stalls`` counts beats
  late by :data:`STALL_WARNING_SECONDS` or more (each also logged at WARNING;
  the :mod:`watchdog <alttprbot.observability.watchdog>` names the code behind
  the long ones)
* ``gc.pause`` (s, distribution, by ``generation``) for every collection of 10ms
  or more, ``gc.seconds`` (counter) for all of them
* ``db_pool.size`` / ``db_pool.in_use`` / ``db_pool.max``
* ``events.pending``: event-bus deliveries still running
* whatever the front ends add with :func:`add_source`: Discord latency and
  guild count, racetime.gg rooms per category.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import os
import statistics
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple

from alttprbot.observability import metrics

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 0.25
STALL_WARNING_SECONDS = 0.5
GC_PAUSE_FLOOR_SECONDS = 0.01

# A source returns (metric name, value, attributes or None) triples.
Sample = Tuple[str, Optional[float], Optional[Dict[str, Any]]]
Source = Callable[[], Iterable[Sample]]

_sources: Dict[str, Source] = {}
_lags_ms: Deque[float] = deque(maxlen=int(metrics.SAMPLE_SECONDS / HEARTBEAT_SECONDS) + 8)
_stalls = 0
_last_beat = time.monotonic()
_tasks: List[asyncio.Task] = []

_gc_started: Dict[int, float] = {}
_gc_pauses: Deque[Tuple[int, float]] = deque(maxlen=500)
_gc_lock = threading.Lock()
_last_cpu: Optional[Tuple[float, float]] = None


def add_source(name: str, source: Source) -> None:
    """Sample ``source`` with the process figures. A front end calls this at startup.

    A source runs on the event loop every sample, so it must be quick and must not
    await. One that raises is skipped for that sample.
    """
    _sources[name] = source


def last_heartbeat() -> float:
    """``time.monotonic()`` of the loop's latest heartbeat; the watchdog reads it."""
    return _last_beat


# --- Event-loop heartbeat ------------------------------------------------------


async def _heartbeat() -> None:
    global _last_beat, _stalls
    while True:
        expected = time.monotonic() + HEARTBEAT_SECONDS
        await asyncio.sleep(HEARTBEAT_SECONDS)
        now = time.monotonic()
        _last_beat = now
        lag = max(0.0, now - expected)
        _lags_ms.append(lag * 1000)
        if lag >= STALL_WARNING_SECONDS:
            _stalls += 1
            logger.warning('Event loop was blocked for %.2fs', lag)


# --- Garbage collection ----------------------------------------------------------


def _gc_callback(phase: str, info: Dict[str, Any]) -> None:
    generation = info.get('generation', -1)
    if phase == 'start':
        _gc_started[generation] = time.perf_counter()
        return
    started = _gc_started.pop(generation, None)
    if started is None:
        return
    with _gc_lock:
        _gc_pauses.append((generation, time.perf_counter() - started))


def _drain_gc() -> List[Tuple[int, float]]:
    with _gc_lock:
        pauses = list(_gc_pauses)
        _gc_pauses.clear()
    return pauses


# --- Sampling ----------------------------------------------------------------------


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method='inclusive')[int(pct) - 1]


def _cpu_percent() -> Optional[float]:
    global _last_cpu
    times = os.times()
    now = (time.monotonic(), times.user + times.system)
    previous, _last_cpu = _last_cpu, now
    if previous is None or now[0] <= previous[0]:
        return None
    return round((now[1] - previous[1]) / (now[0] - previous[0]) * 100, 1)


def _rss_mb() -> Optional[float]:
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / 1_048_576, 1)
    except Exception:
        return None


def _db_pool() -> Iterable[Sample]:
    try:
        from tortoise import connections
        pool = getattr(connections.get('default'), '_pool', None)
    except Exception:
        return []
    if pool is None:
        return []
    size, free, maximum = (getattr(pool, a, None) for a in ('size', 'freesize', 'maxsize'))
    out: List[Sample] = [('db_pool.size', size, None), ('db_pool.max', maximum, None)]
    if isinstance(size, int) and isinstance(free, int):
        out.append(('db_pool.in_use', size - free, None))
    return out


def _events_pending() -> Iterable[Sample]:
    from alttprbot.events import bus
    return [('events.pending', bus.pending_count(), None)]


def _task_count() -> Optional[int]:
    try:
        return len(asyncio.all_tasks())
    except RuntimeError:  # no running loop
        return None


def collect() -> List[Sample]:
    """Everything one sample sends, as (name, value, attributes) triples."""
    lags = list(_lags_ms)
    _lags_ms.clear()
    samples: List[Sample] = [
        ('process.cpu', _cpu_percent(), None),
        ('process.memory_rss', _rss_mb(), None),
        ('process.asyncio_tasks', _task_count(), None),
        ('process.threads', threading.active_count(), None),
        ('loop.lag_p50', _percentile(lags, 50), None),
        ('loop.lag_p95', _percentile(lags, 95), None),
        ('loop.lag_max', max(lags) if lags else None, None),
    ]
    for name, source in [('db_pool', _db_pool), ('events', _events_pending), *_sources.items()]:
        try:
            samples.extend(source())
        except Exception:
            logger.debug('Metrics source %s failed', name, exc_info=True)
    return samples


_UNITS = {
    'process.cpu': 'percent',
    'process.memory_rss': 'megabyte',
    'loop.lag_p50': 'millisecond',
    'loop.lag_p95': 'millisecond',
    'loop.lag_max': 'millisecond',
    'discord.latency': 'millisecond',
}

_last_stalls = 0


def emit() -> None:
    global _last_stalls
    for name, value, attributes in collect():
        metrics.gauge(name, value, unit=_UNITS.get(name), attributes=attributes)
    if _stalls > _last_stalls:
        metrics.count('loop.stalls', _stalls - _last_stalls)
        _last_stalls = _stalls
    for generation, seconds in _drain_gc():
        attrs = {'generation': str(generation)}
        metrics.count('gc.seconds', round(seconds, 4), unit='second', attributes=attrs)
        if seconds >= GC_PAUSE_FLOOR_SECONDS:
            metrics.distribution('gc.pause', seconds, unit='second', attributes=attrs)


async def _sample_forever() -> None:
    _cpu_percent()  # prime the CPU delta
    while True:
        await asyncio.sleep(metrics.SAMPLE_SECONDS)
        try:
            emit()
        except Exception:
            logger.exception('Sampling runtime metrics failed')


def start() -> None:
    """Start the heartbeat, GC timing and (with metrics on) the sampler. Needs a running loop."""
    if _tasks:
        return
    loop = asyncio.get_running_loop()
    _tasks.append(loop.create_task(_heartbeat(), name='observability:heartbeat'))
    if metrics.enabled():
        if _gc_callback not in gc.callbacks:
            gc.callbacks.append(_gc_callback)
        _tasks.append(loop.create_task(_sample_forever(), name='observability:sampler'))


async def stop() -> None:
    for task in _tasks:
        task.cancel()
    await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
    if _gc_callback in gc.callbacks:
        gc.callbacks.remove(_gc_callback)
