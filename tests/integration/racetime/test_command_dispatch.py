"""Tests for the ported command dispatch and race-edit behavior.

``SahasrahBotCoreHandler`` re-adds two behaviors the official upstream
racetime-bot 2.3.0 ``RaceHandler`` does not provide:

* ``chat_message`` that dispatches both ``ex_*`` and ``ex2_*`` command forms,
  preserving case (upstream lowercases the whole message and only routes
  ``ex_*``).
* ``edit`` to change race-room settings via the parent bot's HTTP session.

Handlers are built via ``__new__`` to bypass ``RaceHandler.__init__`` (which
needs a live websocket); we set only the attributes the methods under test read.
See alttprbot/presentation/racetime/handlers/core.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from alttprbot.presentation.racetime.handlers.core import SahasrahBotCoreHandler


def make_handler():
    handler = SahasrahBotCoreHandler.__new__(SahasrahBotCoreHandler)
    handler.command_prefix = "!"
    handler.data = {}
    handler.state = {}
    handler.logger = MagicMock()
    handler.send_message = AsyncMock()
    return handler


def chat_frame(text, **message_overrides):
    message = {
        "message": text,
        "is_bot": False,
        "is_system": False,
        "is_monitor": False,
        "user": {"id": "u1", "name": "Runner"},
    }
    message.update(message_overrides)
    return {"type": "chat.message", "message": message}


async def test_ex_command_dispatched_with_args_and_message():
    handler = make_handler()
    handler.ex_testcmd = AsyncMock()
    await handler.chat_message(chat_frame("!testcmd alpha beta"))
    handler.ex_testcmd.assert_awaited_once()
    args, message = handler.ex_testcmd.await_args.args
    assert args == ["alpha", "beta"]
    assert message["message"] == "!testcmd alpha beta"


async def test_ex2_command_dispatched_with_parsed_args():
    handler = make_handler()
    handler.ex2_testcmd = AsyncMock()
    await handler.chat_message(chat_frame("!testcmd mypreset --branch=Tournament"))
    handler.ex2_testcmd.assert_awaited_once()
    message, positional_args, keyword_args = handler.ex2_testcmd.await_args.args
    # positional_args[0] is the command token, [1] the first real positional.
    assert positional_args == ["!testcmd", "mypreset"]
    # Case must be preserved for keyword values.
    assert keyword_args == {"branch": "Tournament"}


async def test_ex_only_present_does_not_require_ex2():
    handler = make_handler()
    handler.ex_testcmd = AsyncMock()
    # No ex2_testcmd attribute -> only the ex_ path runs, no AttributeError.
    await handler.chat_message(chat_frame("!testcmd"))
    handler.ex_testcmd.assert_awaited_once()


async def test_command_exception_is_echoed_to_chat():
    handler = make_handler()
    handler.ex_boom = AsyncMock(side_effect=RuntimeError("kaboom"))
    await handler.chat_message(chat_frame("!boom"))
    handler.send_message.assert_awaited_once()
    assert "Command raised exception" in handler.send_message.await_args.args[0]
    assert "kaboom" in handler.send_message.await_args.args[0]


async def test_bot_message_is_ignored():
    handler = make_handler()
    handler.ex_testcmd = AsyncMock()
    await handler.chat_message(chat_frame("!testcmd", is_bot=True))
    handler.ex_testcmd.assert_not_awaited()


async def test_system_message_is_ignored():
    handler = make_handler()
    handler.ex_testcmd = AsyncMock()
    await handler.chat_message(chat_frame("!testcmd", is_system=True))
    handler.ex_testcmd.assert_not_awaited()


async def test_non_command_message_is_ignored():
    handler = make_handler()
    handler.ex_testcmd = AsyncMock()
    await handler.chat_message(chat_frame("just chatting"))
    handler.ex_testcmd.assert_not_awaited()


async def test_api_injected_synthetic_frame_dispatches():
    # Mirrors the /api/racetime/cmd synthetic payload: message text lives at
    # data['message']['message'], with is_monitor True.
    handler = make_handler()
    handler.ex2_newrace = AsyncMock()
    frame = {
        "type": "message.chat",
        "message": {
            "message": "!newrace mypreset",
            "is_bot": False,
            "is_system": False,
            "is_monitor": True,
        },
    }
    await handler.chat_message(frame)
    handler.ex2_newrace.assert_awaited_once()
    message, positional_args, _ = handler.ex2_newrace.await_args.args
    assert message["is_monitor"] is True
    assert positional_args[1] == "mypreset"


# --- edit() ---


class _FakeResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _open_race_data(name="alttpr/test-room", status="open"):
    return {
        "name": name,
        "status": {"value": status},
        "goal": {"name": "Beat the game", "custom": False},
        "unlisted": False,
        "info_user": "some info",
        "start_delay": "PT15S",
        "time_limit": "PT24H0M0S",
        "streaming_required": True,
        "auto_start": True,
        "allow_comments": True,
        "hide_comments": False,
        "allow_prerace_chat": True,
        "allow_midrace_chat": True,
        "allow_non_entrant_chat": False,
        "chat_message_delay": "PT0S",
    }


def make_edit_handler(race_data):
    handler = SahasrahBotCoreHandler.__new__(SahasrahBotCoreHandler)
    handler.logger = MagicMock()
    handler.data = race_data
    post = MagicMock(return_value=_FakeResponse(200))
    handler.bot = SimpleNamespace(
        http=SimpleNamespace(post=post),
        http_uri=lambda url: f"https://racetime.gg{url}",
        ssl_context=None,
        access_token="tok",
    )
    return handler, post


async def test_edit_posts_to_edit_endpoint_with_overrides():
    handler, post = make_edit_handler(_open_race_data())
    result = await handler.edit(hide_comments=True)
    assert result is True
    post.assert_called_once()
    kwargs = post.call_args.kwargs
    assert kwargs["url"] == "https://racetime.gg/o/alttpr/test-room/edit"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    settings = kwargs["data"]
    assert settings["hide_comments"] is True
    assert settings["info_user"] == "some info"
    assert settings["goal"] == "Beat the game"
    assert settings["start_delay"] == 15
    assert settings["time_limit"] == 24


async def test_edit_rejects_finished_race():
    handler, post = make_edit_handler(_open_race_data(status="finished"))
    with pytest.raises(Exception):
        await handler.edit(hide_comments=True)
    post.assert_not_called()


async def test_edit_prunes_open_only_settings_when_not_open():
    # For a race that is no longer open/invitational, open-only keys are dropped.
    handler, post = make_edit_handler(_open_race_data(status="pending"))
    await handler.edit(hide_comments=True)
    settings = post.call_args.kwargs["data"]
    for pruned in ("start_delay", "time_limit", "streaming_required", "auto_start"):
        assert pruned not in settings
    assert settings["hide_comments"] is True
