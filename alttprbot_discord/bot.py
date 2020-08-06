import os
import asyncio
import importlib
import random
import sys
import traceback
from alttprbot.exceptions import SahasrahBotException

import discord
from discord.ext import commands

from alttprbot.database import config
from discord_sentry_reporting import use_sentry


async def determine_prefix(bot, message):
    if message.guild is None:
        return "$"

    prefix = await config.get(message.guild.id, "CommandPrefix")
    return "$" if prefix is False else prefix


discordbot = commands.Bot(
    command_prefix=determine_prefix
)

use_sentry(discordbot, dsn=os.environ.get("SENTRY_URL"))

discordbot.load_extension("alttprbot_discord.cogs.admin")
discordbot.load_extension("alttprbot_discord.cogs.alttprgen")
discordbot.load_extension("alttprbot_discord.cogs.audit")
discordbot.load_extension("alttprbot_discord.cogs.bontamw")
discordbot.load_extension("alttprbot_discord.cogs.daily")
# discordbot.load_extension("alttprbot_discord.cogs.league")
discordbot.load_extension("alttprbot_discord.cogs.misc")
discordbot.load_extension("alttprbot_discord.cogs.moderation")
discordbot.load_extension("alttprbot_discord.cogs.nickname")
discordbot.load_extension("alttprbot_discord.cogs.role")
discordbot.load_extension("alttprbot_discord.cogs.smvaria")
discordbot.load_extension("alttprbot_discord.cogs.smz3")
# discordbot.load_extension("alttprbot_discord.cogs.tournament")
discordbot.load_extension("alttprbot_discord.cogs.voicerole")

if importlib.util.find_spec('jishaku'):
    discordbot.load_extension('jishaku')

if importlib.util.find_spec('sahasrahbot_private.stupid_memes'):
    discordbot.load_extension('sahasrahbot_private.stupid_memes')


@discordbot.event
async def on_command_error(ctx, error):
    riplink = discord.utils.get(ctx.bot.emojis, name='RIPLink')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)
    print(error)
    if isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.message.add_reaction('🚫')
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.UserInputError):
        if riplink is None:
            riplink = '👎'
        await ctx.send(error)
    else:
        if riplink is None:
            riplink = '👎'
        error_to_display = error.original if hasattr(
            error, 'original') else error

        await ctx.message.add_reaction(riplink)

        if not isinstance(error_to_display, SahasrahBotException):
            await ctx.send(f"```{repr(error_to_display)}```")
            raise error_to_display
        else:
            await ctx.send(error_to_display)


@discordbot.event
async def on_command(ctx):
    await ctx.message.add_reaction('⌚')


@discordbot.event
async def on_command_completion(ctx):
    await ctx.message.add_reaction('✅')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)


@discordbot.event
async def on_message(message):
    # override discord.py's process_commands coroutine in the commands.Bot class
    # this allows SpeedGamingBot to issue commands to SahasrahBot
    if message.author.bot and not message.author.id == 344251539931660288:
        return

    ctx = await discordbot.get_context(message)
    await discordbot.invoke(ctx)

    if discordbot.user in message.mentions:
        emoji = discord.utils.get(discordbot.emojis, name='SahasrahBot')
        if emoji:
            await asyncio.sleep(random.random()*5)
            await message.add_reaction(emoji)
