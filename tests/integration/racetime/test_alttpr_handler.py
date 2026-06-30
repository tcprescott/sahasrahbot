"""Characterization tests for the ALTTPR racetime GameHandler.!newrace command.

We feed fake message/arg structures to ``ex2_newrace`` and mock the seed
generator so no real seed is rolled. ``set_bot_raceinfo``/``send_message`` are
mocked to capture output.

See alttprbot/presentation/racetime/handlers/alttpr.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alttprbot.services.seedgen import preset
from alttprbot.presentation.racetime.handlers import alttpr as alttpr_handler
from alttprbot.presentation.racetime.handlers.alttpr import GameHandler

PLAIN_MSG = {"is_monitor": False, "user": {"id": "runner", "name": "Runner"}}


def make_handler(seed_rolled=False, state=None):
    handler = GameHandler.__new__(GameHandler)
    handler.state = {} if state is None else state
    handler.seed_rolled = seed_rolled
    handler.command_prefix = "!"
    handler.data = {}
    handler.logger = MagicMock()
    handler.send_message = AsyncMock()
    handler.set_bot_raceinfo = AsyncMock()
    return handler


def patch_preset(seed=None, exc=None):
    """Patch generator.ALTTPRPreset; returns the patcher and the generate mock."""
    preset_obj = MagicMock()
    if exc is not None:
        preset_obj.generate = AsyncMock(side_effect=exc)
    else:
        preset_obj.generate = AsyncMock(return_value=seed)
    patcher = patch.object(alttpr_handler.generator, "ALTTPRPreset", return_value=preset_obj)
    return patcher, preset_obj


async def test_requires_preset():
    handler = make_handler()
    await handler.ex2_newrace(PLAIN_MSG, ["newrace"], {})
    handler.send_message.assert_awaited_with("You must specify a preset!")
    assert handler.seed_rolled is False


async def test_already_rolled_short_circuits():
    handler = make_handler(seed_rolled=True)
    await handler.ex2_newrace(PLAIN_MSG, ["newrace", "open"], {})
    assert "already rolled" in handler.send_message.await_args_list[0].args[0]


async def test_happy_path_sets_race_info_and_marks_rolled():
    seed = SimpleNamespace(url="https://alttpr.com/h/X", code=["Bow", "Boots"])
    patcher, preset_obj = patch_preset(seed=seed)
    with patcher as mock_cls:
        handler = make_handler()
        await handler.ex2_newrace(PLAIN_MSG, ["newrace"], {"preset": "open", "branch": "tournament"})

    mock_cls.assert_called_once_with("open")
    handler.set_bot_raceinfo.assert_awaited_once_with("open - https://alttpr.com/h/X - (Bow/Boots)")
    assert handler.seed_rolled is True
    _, kwargs = preset_obj.generate.call_args
    assert kwargs["branch"] == "tournament"
    assert kwargs["allow_quickswap"] is True


async def test_quickswap_keyword_is_forwarded():
    seed = SimpleNamespace(url="https://alttpr.com/h/Y", code=["Hookshot"])
    patcher, preset_obj = patch_preset(seed=seed)
    with patcher:
        handler = make_handler()
        await handler.ex2_newrace(PLAIN_MSG, ["newrace"], {"preset": "open", "quickswap": False})
    _, kwargs = preset_obj.generate.call_args
    assert kwargs["allow_quickswap"] is False


async def test_branch_from_positional_args():
    seed = SimpleNamespace(url="https://alttpr.com/h/Z", code=["Lamp"])
    patcher, preset_obj = patch_preset(seed=seed)
    with patcher as mock_cls:
        handler = make_handler()
        await handler.ex2_newrace(PLAIN_MSG, ["newrace", "open", "beeta"], {})
    mock_cls.assert_called_once_with("open")
    _, kwargs = preset_obj.generate.call_args
    assert kwargs["branch"] == "beeta"


async def test_preset_not_found_is_reported():
    patcher, _ = patch_preset(exc=preset.PresetNotFoundException("no such preset: foo"))
    with patcher:
        handler = make_handler()
        await handler.ex2_newrace(PLAIN_MSG, ["newrace"], {"preset": "foo"})
    handler.send_message.assert_awaited_with("no such preset: foo")
    assert handler.seed_rolled is False


@pytest.mark.parametrize("festive, expected_prefix", [(True, "/festive"), (False, "")])
async def test_festive_keyword_sets_endpoint_prefix(festive, expected_prefix):
    seed = SimpleNamespace(url="https://alttpr.com/h/F", code=["Bow"])
    patcher, preset_obj = patch_preset(seed=seed)
    with patcher:
        handler = make_handler()
        await handler.ex2_newrace(PLAIN_MSG, ["newrace"], {"preset": "open", "festive": festive})
    _, kwargs = preset_obj.generate.call_args
    assert kwargs["endpoint_prefix"] == expected_prefix


async def test_spoiler_race_branch_schedules_spoiler():
    spoiler = SimpleNamespace(
        seed=SimpleNamespace(url="https://alttpr.com/h/S", code=["Bow", "Boots"]),
        spoiler_log_url="https://spoiler/log",
    )
    handler = make_handler()
    handler.schedule_spoiler_race = AsyncMock()
    with patch.object(alttpr_handler.spoilers, "generate_spoiler_game", AsyncMock(return_value=spoiler)) as mock_gen:
        await handler.ex2_newrace(PLAIN_MSG, ["newrace"], {"preset": "open", "spoiler_race": True})

    mock_gen.assert_awaited_once()
    handler.set_bot_raceinfo.assert_awaited_once_with("spoiler open - https://alttpr.com/h/S - (Bow/Boots)")
    handler.schedule_spoiler_race.assert_awaited_once_with("https://spoiler/log", 900)
    assert handler.seed_rolled is True
