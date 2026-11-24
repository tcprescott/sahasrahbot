"""Counts Discord interactions, prefix commands and gateway reconnects for Sentry Metrics.

Slash commands are timed by ``SentryCommandTree`` in ``alttprbot_discord/telemetry.py``.
"""

import time

import discord
from discord.ext import commands

from alttprbot.observability import metrics


class Telemetry(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        metrics.count('discord.interactions', attributes={'type': interaction.type.name})

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        ctx.telemetry_started = time.perf_counter()

    def _prefix_done(self, ctx: commands.Context, error) -> None:
        started = getattr(ctx, 'telemetry_started', None)
        if started is None or ctx.command is None:
            return
        metrics.record_call('discord.commands', started, error,
                            {'command': ctx.command.qualified_name, 'kind': 'prefix'})

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        self._prefix_done(ctx, None)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        self._prefix_done(ctx, error)

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        metrics.count('discord.gateway', attributes={'event': 'connect'})

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        metrics.count('discord.gateway', attributes={'event': 'disconnect'})

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        metrics.count('discord.gateway', attributes={'event': 'resumed'})


async def setup(bot: commands.Bot):
    await bot.add_cog(Telemetry(bot))
