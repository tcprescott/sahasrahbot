import asyncio
import importlib
import random
import sys
import traceback
from alttprbot.exceptions import SahasrahBotException

import discord
from discord.ext import commands

from alttprbot.database import config


async def determine_prefix(bot, message):
    if message.guild is None:
        return "$"

    prefix = await config.get(message.guild.id, "CommandPrefix")
    return "$" if prefix is False else prefix


discordbot = commands.Bot(
    command_prefix=determine_prefix,
)

discordbot.load_extension("alttprbot_discord.cogs.admin")
discordbot.load_extension("alttprbot_discord.cogs.alttprgen")
discordbot.load_extension("alttprbot_discord.cogs.audit")
discordbot.load_extension("alttprbot_discord.cogs.bontamw")
discordbot.load_extension("alttprbot_discord.cogs.daily")
discordbot.load_extension("alttprbot_discord.cogs.league")
discordbot.load_extension("alttprbot_discord.cogs.misc")
discordbot.load_extension("alttprbot_discord.cogs.moderation")
discordbot.load_extension("alttprbot_discord.cogs.nickname")
discordbot.load_extension("alttprbot_discord.cogs.role")
discordbot.load_extension("alttprbot_discord.cogs.smz3gen")
discordbot.load_extension("alttprbot_discord.cogs.tournament")
discordbot.load_extension("alttprbot_discord.cogs.voicerole")

if importlib.util.find_spec('jishaku'):
    discordbot.load_extension('jishaku')

@discordbot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction('⌚', ctx.bot.user)

    riplink = discord.utils.get(ctx.bot.emojis, name='RIPLink')
    if riplink is None:
        riplink = '👎'

    if isinstance(error, commands.CheckFailure):
        await ctx.message.add_reaction('🚫')
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.message.add_reaction('🚫')
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        error_to_display = error.original if hasattr(error, 'original') else error

        await ctx.message.add_reaction(riplink)

        if not isinstance(error_to_display, SahasrahBotException):
            error_channel = await commands.TextChannelConverter().convert(ctx, await config.get(0, "ErrorChannel"))
            if error_channel:
                await error_channel.send(f"```python\n{''.join(traceback.format_exception(etype=type(error_to_display), value=error_to_display, tb=error_to_display.__traceback__))}```")
            try:
                appinfo = await discordbot.application_info()
                await ctx.send(f'Something happened that should not have happened. {appinfo.owner.mention}')
            except discord.errors.HTTPException:
                pass
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
