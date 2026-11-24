"""Name the code that blocks the event loop.

Everything (both bots, the web app, the scheduler) shares one asyncio loop, so one
synchronous stretch freezes all of it, and the code that caused it finishes
normally while everything else only looks slow. Like Wizzrobe's
``loop_watchdog``, a daemon thread watches the heartbeat that
:mod:`alttprbot.observability.runtime` posts four times a second. When the beat is
:data:`STALL_ERROR_SECONDS` late, the thread samples the loop thread's stack
*while it is still blocked*, which is what names the culprit: the innermost frame
in this repository (``alttprbot/alttprgen/spoilers.py:88 in generate``), not the
library line underneath it.

The stall is logged at ERROR on this module's logger, so it becomes a Sentry issue
fingerprinted ``event-loop-blocked`` + culprit and tagged ``loop_blocked_in``. One
report per stall. ``SENTRY_LOOP_WATCHDOG = False`` in ``config.py`` turns it off.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import traceback
from pathlib import Path
from types import FrameType
from typing import Optional

import sentry_sdk

from alttprbot.observability import runtime

logger = logging.getLogger(__name__)

STALL_ERROR_SECONDS = 2.0
CHECK_SECONDS = 0.25

ROOT = Path(__file__).resolve().parent.parent.parent
_OUR_CODE = tuple(str(ROOT / p) for p in ('alttprbot', 'alttprbot_api', 'alttprbot_discord',
                                          'alttprbot_racetime', 'sahasrahbot.py'))


def culprit(frame: Optional[FrameType]) -> str:
    """``path:line in function`` for the innermost frame of our own code in ``frame``'s stack."""
    innermost = None
    while frame is not None:
        filename = frame.f_code.co_filename
        if innermost is None:
            innermost = frame
        if filename.startswith(_OUR_CODE) and not filename.startswith(str(Path(__file__).parent)):
            rel = Path(filename).resolve().relative_to(ROOT).as_posix()
            return f'{rel}:{frame.f_lineno} in {frame.f_code.co_name}'
        frame = frame.f_back
    if innermost is None:
        return 'unknown'
    return f'{Path(innermost.f_code.co_filename).name}:{innermost.f_lineno} in {innermost.f_code.co_name}'


class Watchdog:
    def __init__(self, loop_thread_id: int) -> None:
        self.loop_thread_id = loop_thread_id
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name='loop-watchdog', daemon=True)
        self._reported_beat: Optional[float] = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def check(self) -> Optional[str]:
        """Report a stall if the loop is blocked now. Returns the culprit when it reports."""
        beat = runtime.last_heartbeat()
        late = time.monotonic() - beat - runtime.HEARTBEAT_SECONDS
        if late < STALL_ERROR_SECONDS or self._reported_beat == beat:
            return None
        self._reported_beat = beat
        frame = sys._current_frames().get(self.loop_thread_id)
        where = culprit(frame)
        stack = ''.join(traceback.format_stack(frame)) if frame is not None else ''
        with sentry_sdk.new_scope() as scope:
            scope.set_tag('loop_blocked_in', where)
            scope.fingerprint = ['event-loop-blocked', where]
            logger.error('Event loop blocked for %.1fs+ in %s\n%s', late, where, stack)
        return where

    def _run(self) -> None:
        while not self._stop.wait(CHECK_SECONDS):
            try:
                self.check()
            except Exception:
                logger.debug('Loop watchdog check failed', exc_info=True)


_watchdog: Optional[Watchdog] = None


def start() -> None:
    """Watch the calling thread's loop. Call from the loop thread, after ``runtime.start()``."""
    global _watchdog
    if _watchdog is None:
        _watchdog = Watchdog(threading.get_ident())
        _watchdog.start()
