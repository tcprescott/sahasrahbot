"""A single-worker async queue for fire-and-forget notification work.

Services enqueue coroutines that touch a presentation surface (Discord DM,
RaceTime chat message, etc.). A single background worker drains the queue, so the
caller never blocks on a rate limit and the service tier never awaits the bot
singletons directly. Items enqueued before :func:`start` runs simply wait in the
queue and drain once the worker comes up — this is what makes gateway
registration ordering during boot safe.

Lifecycle is owned by ``sahasrahbot.py``: :func:`start` after the event loop is
running, :func:`stop` during graceful shutdown.
"""

import asyncio
import contextlib
import logging
from typing import Awaitable, Optional

logger = logging.getLogger(__name__)

_queue: "asyncio.Queue[Awaitable]" = asyncio.Queue()
_worker: Optional[asyncio.Task] = None


def enqueue(coro: Awaitable) -> None:
    """Schedule a coroutine to run on the notification worker."""
    _queue.put_nowait(coro)


async def _run_worker() -> None:
    while True:
        coro = await _queue.get()
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a failed notification must not kill the worker
            logger.exception("notify worker: enqueued task raised")
        finally:
            _queue.task_done()


def start() -> None:
    """Start the worker task if it is not already running."""
    global _worker
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_run_worker(), name="notify-worker")
        logger.info("notify worker started")


async def stop() -> None:
    """Cancel the worker and wait for it to finish."""
    global _worker
    if _worker is not None:
        _worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _worker
        _worker = None
        logger.info("notify worker stopped")
