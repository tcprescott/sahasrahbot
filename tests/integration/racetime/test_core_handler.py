"""Characterization tests for SahasrahBotCoreHandler command/lock logic.

Handlers are instantiated via ``__new__`` to bypass ``RaceHandler.__init__``
(which needs a live websocket connection); we set just the attributes the
methods under test touch and mock ``send_message``/``set_bot_raceinfo``.

``can_monitor(message)`` is ``message.get('is_monitor', False)``, so monitor
status is controlled by that key.

See alttprbot/presentation/racetime/handlers/core.py.
"""

from unittest.mock import AsyncMock, MagicMock

from alttprbot.presentation.racetime.handlers.core import SahasrahBotCoreHandler

MONITOR_MSG = {"is_monitor": True, "user": {"id": "mod", "name": "Mod"}}
PLAIN_MSG = {"is_monitor": False, "user": {"id": "runner", "name": "Runner"}}


def make_handler(state=None, seed_rolled=False):
    handler = SahasrahBotCoreHandler.__new__(SahasrahBotCoreHandler)
    handler.state = {} if state is None else state
    handler.seed_rolled = seed_rolled
    handler.command_prefix = "!"
    handler.data = {}
    handler.logger = MagicMock()
    handler.send_message = AsyncMock()
    handler.set_bot_raceinfo = AsyncMock()
    return handler


async def test_is_locked_true_when_seed_already_rolled():
    handler = make_handler(seed_rolled=True)
    assert await handler.is_locked(PLAIN_MSG) is True
    assert "already rolled" in handler.send_message.await_args.args[0]


async def test_is_locked_true_when_locked_and_not_monitor():
    handler = make_handler(state={"locked": True})
    assert await handler.is_locked(PLAIN_MSG) is True
    assert "locked" in handler.send_message.await_args.args[0].lower()


async def test_is_locked_false_when_locked_but_monitor():
    handler = make_handler(state={"locked": True})
    assert await handler.is_locked(MONITOR_MSG) is False
    handler.send_message.assert_not_awaited()


async def test_is_locked_false_when_open():
    handler = make_handler()
    assert await handler.is_locked(PLAIN_MSG) is False
    handler.send_message.assert_not_awaited()


async def test_ex_lock_locks_for_monitor():
    handler = make_handler(state={"locked": False})
    await handler.ex_lock([], MONITOR_MSG)
    assert handler.state["locked"] is True
    assert "Lock initiated" in handler.send_message.await_args.args[0]


async def test_ex_lock_denied_for_non_monitor_leaves_state():
    handler = make_handler(state={"locked": False})
    await handler.ex_lock([], PLAIN_MSG)
    assert handler.state["locked"] is False
    assert "only race monitors" in handler.send_message.await_args.args[0]


async def test_ex_unlock_unlocks_for_monitor():
    handler = make_handler(state={"locked": True})
    await handler.ex_unlock([], MONITOR_MSG)
    assert handler.state["locked"] is False


async def test_ex_unlock_denied_for_non_monitor_leaves_state():
    handler = make_handler(state={"locked": True})
    await handler.ex_unlock([], PLAIN_MSG)
    assert handler.state["locked"] is True
    assert "only race monitors" in handler.send_message.await_args.args[0]


async def test_ex_cancel_resets_seed_state():
    handler = make_handler(seed_rolled=True)
    await handler.ex_cancel([], PLAIN_MSG)
    assert handler.seed_rolled is False
    handler.set_bot_raceinfo.assert_awaited_once_with("New Race")
