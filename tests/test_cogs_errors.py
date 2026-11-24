"""The error-handler cog (alttprbot_discord/cogs/errors.py) and the telemetry cog
(alttprbot_discord/cogs/telemetry.py)."""

from types import SimpleNamespace
from unittest import mock

import discord
import pytest
from discord import app_commands
from discord.ext import commands

from alttprbot_discord.cogs import errors as errors_cog
from alttprbot_discord.cogs import telemetry as telemetry_cog
from tests.discord_fakes import FakeBot, FakeContext, FakeInteraction, emoji

RIP = "<:RIPLink:1>"


def http_error(cls, status, text):
    return cls(mock.Mock(status=status, reason="x"), text)


@pytest.fixture
def cog():
    return errors_cog.Errors(FakeBot(emojis=[emoji("RIPLink")]))


def test_registers_tree_error_handler():
    bot = FakeBot()
    errors_cog.Errors(bot)
    bot.tree.error.assert_called_once()


# ---------------------------------------------------------------------------
# App command errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error, expected",
    [
        (app_commands.CommandInvokeError(mock.Mock(), ValueError("bad value")), f"{RIP} `ValueError` : bad value"),
        (
            app_commands.CommandInvokeError(mock.Mock(), http_error(discord.Forbidden, 403, "Missing Access")),
            f"{RIP} `Forbidden` : Missing Access",
        ),
        (app_commands.CheckFailure("nope"), f"{RIP} `CheckFailure` : nope"),
        (
            app_commands.CommandOnCooldown(app_commands.Cooldown(1, 10), 4.2),
            f"{RIP} Command is on cooldown, wait `4.20s` !",
        ),
    ],
)
async def test_app_command_error_messages(cog, error, expected):
    interaction = FakeInteraction()

    await cog.get_app_command_error(interaction, error)

    interaction.response.send_message.assert_awaited_once_with(content="There is an error.", ephemeral=True)
    interaction.edit_original_response.assert_awaited_once_with(content=expected)


async def test_app_command_invoke_error_is_logged(cog):
    error = app_commands.CommandInvokeError(mock.Mock(), ValueError("x"))
    await cog.get_app_command_error(FakeInteraction(), error)
    cog.bot.logger.error.assert_called_once_with("Error during interaction", exc_info=error)


async def test_app_command_error_after_response_still_edits(cog):
    interaction = FakeInteraction()
    interaction.response.send_message.side_effect = discord.errors.InteractionResponded(interaction)
    await cog.get_app_command_error(interaction, app_commands.CheckFailure("late"))
    interaction.edit_original_response.assert_awaited_once()


async def test_app_command_not_found_reraises(cog):
    interaction = FakeInteraction()
    error = app_commands.CommandNotFound("gone", [])
    with pytest.raises(app_commands.CommandNotFound):
        await cog.get_app_command_error(interaction, error)
    assert "desynchronization" in interaction.edit_original_response.await_args.kwargs["content"]


async def test_unknown_app_command_error_is_logged_and_reraised(cog):
    error = app_commands.AppCommandError("weird")
    with pytest.raises(app_commands.AppCommandError):
        await cog.get_app_command_error(FakeInteraction(), error)
    cog.bot.logger.error.assert_called_once_with(msg="AppCommandError", exc_info=error)
    assert cog.bot.logger.name == "discord.get_app_command_error"


@pytest.mark.parametrize(
    "original, expected",
    [
        (discord.errors.InteractionResponded(mock.Mock()), "This interaction has already been responded to before"),
        (http_error(discord.Forbidden, 403, "no"), "`Forbidden` : no"),
        (KeyError("k"), "`KeyError` : 'k'"),
    ],
)
def test_invoke_error_message(original, expected):
    assert errors_cog._invoke_error_message(original) == expected


# ---------------------------------------------------------------------------
# Prefix command errors
# ---------------------------------------------------------------------------


def prefix_ctx(cog):
    ctx = FakeContext(bot=cog.bot)
    ctx.command = SimpleNamespace(name="rr", clean_params={"group_id": None, "role": None})
    message = SimpleNamespace(edit=mock.AsyncMock())
    ctx.send.return_value = message
    return ctx, message


def missing_perms(cls, *perms):
    return cls(list(perms))


@pytest.mark.parametrize(
    "error, expected",
    [
        (commands.MissingRequiredArgument(mock.Mock(name="x")), "Something is missing. `$rr <group_id> <role>`"),
        (commands.MemberNotFound("bob"), "Member `\"bob\"` not found ! Don't hesitate to ping the requested member."),
        (missing_perms(commands.BotMissingPermissions, "manage_roles"),
         "The bot require the following permissions: `manage_roles`."),
        (missing_perms(commands.MissingPermissions, "manage_roles", "ban_members"),
         "Your account require the following permissions: `manage_roles` `ban_members`."),
        (commands.CommandInvokeError(ValueError("boom")), "boom"),
        (commands.CommandOnCooldown(commands.Cooldown(1, 10), 3.0, commands.BucketType.user),
         "Command is on cooldown, wait `3.00s` !"),
        (commands.MaxConcurrencyReached(2, commands.BucketType.guild),
         "Max concurrency reached. Maximum number of concurrent invokers allowed: `2`, per `BucketType.guild`."),
        (commands.NotOwner(), "You must own this bot to run this command."),
        (commands.DisabledCommand(), "Sorry this command is disabled."),
        (commands.BadArgument("Not a number"), "Not a number"),
    ],
)
async def test_command_error_messages(cog, error, expected):
    ctx, message = prefix_ctx(cog)
    await cog.get_command_error(ctx, error)
    ctx.send.assert_awaited_once_with("There is an error.")
    message.edit.assert_awaited_once_with(content=f"{RIP} {expected}")


@pytest.mark.parametrize(
    "error",
    [commands.CommandNotFound(), missing_perms(commands.BotMissingPermissions, "send_messages")],
)
async def test_command_errors_with_nothing_more_to_say(cog, error):
    ctx, message = prefix_ctx(cog)
    await cog.get_command_error(ctx, error)
    message.edit.assert_not_awaited()


async def test_unknown_command_error_is_reraised(cog):
    ctx, _ = prefix_ctx(cog)
    with pytest.raises(commands.CommandError):
        await cog.get_command_error(ctx, commands.CommandError("strange"))


async def test_known_issue_hybrid_command_errors_never_reach_app_handler(cog):
    """KNOWN ISSUE, pinned not endorsed: for a hybrid command the handler unwraps
    ``HybridCommandError`` first, so its later "hand it to the app command handler"
    branch can't run, and the unwrapped app-command error is re-raised as unhandled.
    (No cog uses hybrid commands today.)"""
    ctx, _ = prefix_ctx(cog)
    ctx.interaction = FakeInteraction()
    error = commands.HybridCommandError(app_commands.CheckFailure("hybrid"))

    with pytest.raises(app_commands.CheckFailure, match="hybrid"):
        await cog.get_command_error(ctx, error)

    ctx.send.assert_not_awaited()
    ctx.interaction.response.send_message.assert_awaited_once_with(content="There is an error.", ephemeral=True)
    ctx.interaction.edit_original_response.assert_not_awaited()


async def test_view_and_modal_errors_ignore_forbidden(cog):
    forbidden = http_error(discord.Forbidden, 403, "x")
    await cog.get_view_error(FakeInteraction(), forbidden, None)
    await cog.get_modal_error(FakeInteraction(), forbidden)
    cog.bot.logger.error.assert_not_called()

    with pytest.raises(RuntimeError):
        await cog.get_view_error(FakeInteraction(), RuntimeError("view"), None)
    with pytest.raises(RuntimeError):
        await cog.get_modal_error(FakeInteraction(), RuntimeError("modal"))
    assert cog.bot.logger.error.call_count == 2


async def test_on_error_prints(cog, capsys):
    await cog.get_error("on_message", 1, x=2)
    assert "(event) on_message, (args) (1,), (kwargs) {'x': 2}" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


@pytest.fixture
def metrics(monkeypatch):
    fake = SimpleNamespace(count=mock.Mock(), record_call=mock.Mock())
    monkeypatch.setattr(telemetry_cog, "metrics", fake)
    return fake


async def test_telemetry_counts_interactions_and_gateway(metrics):
    cog = telemetry_cog.Telemetry(FakeBot())
    await cog.on_interaction(SimpleNamespace(type=discord.InteractionType.component))
    await cog.on_connect()
    await cog.on_disconnect()
    await cog.on_resumed()
    assert [c.args[0] for c in metrics.count.call_args_list] == ["discord.interactions"] + ["discord.gateway"] * 3
    assert [c.kwargs["attributes"] for c in metrics.count.call_args_list] == [
        {"type": "component"}, {"event": "connect"}, {"event": "disconnect"}, {"event": "resumed"},
    ]


async def test_telemetry_times_prefix_commands(metrics):
    cog = telemetry_cog.Telemetry(FakeBot())
    ctx = SimpleNamespace(command=SimpleNamespace(qualified_name="reactionrole create"))
    error = commands.CommandError("x")

    await cog.on_command(ctx)
    await cog.on_command_completion(ctx)
    await cog.on_command_error(ctx, error)
    await cog.on_command_error(SimpleNamespace(command=None), error)  # never started: ignored

    assert metrics.record_call.call_count == 2
    prefix, started, exc, attrs = metrics.record_call.call_args_list[1].args
    assert (prefix, exc, attrs) == ("discord.commands", error, {"command": "reactionrole create", "kind": "prefix"})
    assert started == ctx.telemetry_started
