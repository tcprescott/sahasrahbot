"""Sentry for the Discord bot: every command traced, counted and timed.

* :class:`SentryCommandTree` wraps each slash command and context-menu call:
  its own Sentry trace (op ``discord.command``), tags ``discord_command``,
  ``discord_guild_id``, ``discord_user_id`` and ``discord_channel_id`` on any event
  or log it raises (so the Errors cog's reports say which command failed for
  whom), and ``discord.commands.calls`` / ``discord.commands.duration`` (ms) by
  ``command``, ``kind`` and ``outcome``. ``discord.commands.delay`` (ms) is how
  long Discord took to hand us the interaction.
* The ``Telemetry`` cog (``cogs/telemetry.py``) counts every interaction by type
  (``discord.interactions``), prefix commands (``discord.commands.*`` with
  ``kind=prefix``) and gateway connects, disconnects and resumes
  (``discord.gateway``).
* :func:`runtime_source` feeds the 30-second sampler: ``discord.latency`` (ms),
  ``discord.guilds`` and ``discord.ready``.
"""

import time

import discord
import sentry_sdk
from discord import app_commands

from alttprbot.observability import metrics
from alttprbot.observability.sentry import sentry_tags


def _command_name(interaction: discord.Interaction) -> str:
    command = interaction.command
    if command is not None:
        return getattr(command, 'qualified_name', None) or command.name
    data = interaction.data or {}
    return str(data.get('name') or 'unknown')


def _kind(interaction: discord.Interaction) -> str:
    if interaction.type is discord.InteractionType.autocomplete:
        return 'autocomplete'
    command_type = (interaction.data or {}).get('type')
    return {2: 'user menu', 3: 'message menu'}.get(command_type, 'slash')


class SentryCommandTree(app_commands.CommandTree):
    """A ``CommandTree`` that traces and times each app command it runs."""

    async def _call(self, interaction: discord.Interaction) -> None:
        name = _command_name(interaction)
        kind = _kind(interaction)
        started = time.perf_counter()
        delay_ms = (discord.utils.utcnow() - interaction.created_at).total_seconds() * 1000
        error = None
        with sentry_sdk.isolation_scope(), sentry_tags(
                discord_command=name,
                discord_guild_id=interaction.guild_id,
                discord_channel_id=interaction.channel_id,
                discord_user_id=interaction.user.id if interaction.user else None):
            sentry_sdk.new_trace()
            if interaction.user is not None:
                sentry_sdk.set_user({'id': str(interaction.user.id), 'username': str(interaction.user)})
            with sentry_sdk.start_span(name=f'/{name}', attributes={'sentry.op': 'discord.command'}):
                try:
                    await super()._call(interaction)
                except BaseException as e:
                    error = e
                    raise
                finally:
                    if error is None and interaction.command_failed:
                        error = RuntimeError('command failed')
                    attrs = {'command': _command_name(interaction), 'kind': kind}
                    metrics.record_call('discord.commands', started, error, attrs)
                    if kind != 'autocomplete':
                        metrics.distribution('discord.commands.delay', max(delay_ms, 0.0),
                                             unit='millisecond', attributes=attrs)


def runtime_source(client: discord.Client):
    """Gauges for :func:`alttprbot.observability.runtime.add_source`."""
    def sample():
        ready = client.is_ready()
        latency = client.latency
        return [
            ('discord.ready', 1 if ready else 0, None),
            ('discord.guilds', len(client.guilds) if ready else None, None),
            ('discord.latency', round(latency * 1000, 1) if ready and latency == latency and latency != float('inf') else None, None),
        ]
    return sample

