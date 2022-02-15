import importlib
import os
import logging
import io

import discord
from discord.ext import commands
from discord.ext.commands import errors
from discord.ext.commands.core import guild_only
from discord_sentry_reporting import use_sentry

from alttprbot_discord.util import config
from config import Config as c

config.init()


async def determine_prefix(bot, message):
    if message.guild is None:
        return "$"

    prefix = await message.guild.config_get("CommandPrefix", "$")
    return prefix

intents = discord.Intents.default()
intents.members = True  # pylint: disable=assigning-non-slot

discordbot = commands.Bot(
    command_prefix=determine_prefix,
    allowed_mentions=discord.AllowedMentions(
        everyone=False,
        users=True,
        roles=False
    ),
    intents=intents,
    debug_guild=508335685044928540 if c.DEBUG else None
)

if os.environ.get("SENTRY_URL"):
    use_sentry(discordbot, dsn=os.environ.get("SENTRY_URL"))

discordbot.load_extension("alttprbot_discord.cogs.alttprgen")
discordbot.load_extension("alttprbot_discord.cogs.bontamw")
discordbot.load_extension("alttprbot_discord.cogs.daily")
discordbot.load_extension("alttprbot_discord.cogs.discord_servers")
# discordbot.load_extension("alttprbot_discord.cogs.guildconfig")
discordbot.load_extension("alttprbot_discord.cogs.misc")
discordbot.load_extension("alttprbot_discord.cogs.nickname")
discordbot.load_extension("alttprbot_discord.cogs.racetime_tools")
discordbot.load_extension("alttprbot_discord.cogs.role")
discordbot.load_extension("alttprbot_discord.cogs.sgdailies")
discordbot.load_extension("alttprbot_discord.cogs.sgl")
discordbot.load_extension("alttprbot_discord.cogs.tournament")
discordbot.load_extension("alttprbot_discord.cogs.voicerole")
discordbot.load_extension("alttprbot_discord.cogs.multiworld")
discordbot.load_extension("alttprbot_discord.cogs.generator")
discordbot.load_extension("alttprbot_discord.cogs.inquiry")

if c.DEBUG:
    discordbot.load_extension("alttprbot_discord.cogs.test")


if importlib.util.find_spec('jishaku'):
    discordbot.load_extension('jishaku')

if importlib.util.find_spec('sahasrahbot_private'):
    discordbot.load_extension('sahasrahbot_private.stupid_memes')


@discordbot.event
async def on_command_error(ctx, error):
    riplink = discord.utils.get(ctx.bot.emojis, name='RIPLink')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)
    logging.info(error)
    if isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.message.add_reaction('🚫')
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.UserInputError):
        if riplink is None:
            riplink = '👎'
        await ctx.reply(error)
    else:
        if riplink is None:
            riplink = '👎'
        error_to_display = error.original if hasattr(
            error, 'original') else error

        await ctx.message.add_reaction(riplink)

        errorstr = repr(error_to_display)
        if len(errorstr) < 1990:
            await ctx.reply(f"```{errorstr}```")
        else:
            await ctx.reply(
                content="An error occured, please see attachment for the full message.",
                file=discord.File(io.StringIO(error_to_display), filename="error.txt")
            )
        raise error_to_display


@discordbot.event
async def on_application_command_error(ctx, error):
    logging.info(error)
    if isinstance(error, commands.CheckFailure):
        await ctx.respond("You are not authorized to use this command here.", ephemeral=True)
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.respond("You are not authorized to use this command here.", ephemeral=True)
    elif isinstance(error, commands.UserInputError):
        await ctx.respond(error)
    else:
        error_to_display = error.original if hasattr(error, 'original') else error

        errorstr = repr(error_to_display)
        if len(errorstr) < 1990:
            await ctx.respond(f"```{errorstr}```")
        else:
            await ctx.respond(
                content="An error occured, please see attachment for the full message.",
                file=discord.File(io.StringIO(error_to_display), filename="error.txt")
            )
        raise error_to_display


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

    if ctx.command is not None:
        discordbot.dispatch('command', ctx)
        try:
            if await discordbot.can_run(ctx, call_once=True):
                await ctx.command.invoke(ctx)
            else:
                raise errors.CheckFailure('The global check once functions failed.')
        except errors.CommandError as exc:
            await ctx.command.dispatch_error(ctx, exc)
        else:
            discordbot.dispatch('command_completion', ctx)
    # elif ctx.invoked_with:
    #     exc = errors.CommandNotFound(
    #         'Command "{}" is not found'.format(ctx.invoked_with))
    #     discordbot.dispatch('command_error', ctx, exc)
