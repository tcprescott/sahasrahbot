import importlib
import os
import logging
import io

import discord
from discord.ext import commands
from discord.ext.commands import errors
from discord_sentry_reporting import use_sentry

from alttprbot_discord.util import config

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
    intents=intents
)


if os.environ.get("SENTRY_URL"):
    use_sentry(discordbot, dsn=os.environ.get("SENTRY_URL"))

discordbot.load_extension("alttprbot_discord.cogs.admin")
discordbot.load_extension("alttprbot_discord.cogs.aqttp")
discordbot.load_extension("alttprbot_discord.cogs.alttprgen")
discordbot.load_extension("alttprbot_discord.cogs.audit")
discordbot.load_extension("alttprbot_discord.cogs.bontamw")
discordbot.load_extension("alttprbot_discord.cogs.daily")
discordbot.load_extension("alttprbot_discord.cogs.discord_servers")
# discordbot.load_extension("alttprbot_discord.cogs.guildconfig")
# discordbot.load_extension("alttprbot_discord.cogs.league")
discordbot.load_extension("alttprbot_discord.cogs.misc")
discordbot.load_extension("alttprbot_discord.cogs.moderation")
discordbot.load_extension("alttprbot_discord.cogs.nickname")
discordbot.load_extension("alttprbot_discord.cogs.role")
discordbot.load_extension("alttprbot_discord.cogs.sgdailies")
discordbot.load_extension("alttprbot_discord.cogs.supermetroid")
discordbot.load_extension("alttprbot_discord.cogs.smz3")
discordbot.load_extension("alttprbot_discord.cogs.sgl")
discordbot.load_extension("alttprbot_discord.cogs.tournament")
discordbot.load_extension("alttprbot_discord.cogs.voicerole")

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

    # replace the bot's invoke coroutine a modified version
    # this allows the bot to begin "typing" when processing a command
    if ctx.command is not None:
        discordbot.dispatch('command', ctx)
        try:
            if await discordbot.can_run(ctx, call_once=True):
                async with ctx.typing():
                    await ctx.command.invoke(ctx)
            else:
                raise errors.CheckFailure(
                    'The global check once functions failed.')
        except errors.CommandError as exc:
            await ctx.command.dispatch_error(ctx, exc)
        else:
            discordbot.dispatch('command_completion', ctx)
    # elif ctx.invoked_with:
    #     exc = errors.CommandNotFound(
    #         'Command "{}" is not found'.format(ctx.invoked_with))
    #     discordbot.dispatch('command_error', ctx, exc)
