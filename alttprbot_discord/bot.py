import importlib
import os
import logging
import io

import discord
from discord.ext import commands
from discord_sentry_reporting import use_sentry
from sentry_sdk import push_scope

from alttprbot_discord.util import config
from config import Config as c

config.init()

intents = discord.Intents.default()
intents.members = True  # pylint: disable=assigning-non-slot

discordbot = commands.Bot(
    command_prefix=commands.when_mentioned_or("$"),
    allowed_mentions=discord.AllowedMentions(
        everyone=False,
        users=True,
        roles=False
    ),
    intents=intents
)

discordbot.logger = logging.getLogger('discord')

if os.environ.get("SENTRY_URL"):
    use_sentry(discordbot, dsn=os.environ.get("SENTRY_URL"))

async def load_extensions():
    await discordbot.load_extension("alttprbot_discord.cogs.errors")
    await discordbot.load_extension("alttprbot_discord.cogs.bontamw")
    await discordbot.load_extension("alttprbot_discord.cogs.daily")
    await discordbot.load_extension("alttprbot_discord.cogs.discord_servers")
    await discordbot.load_extension("alttprbot_discord.cogs.misc")
    await discordbot.load_extension("alttprbot_discord.cogs.nickname")
    await discordbot.load_extension("alttprbot_discord.cogs.racetime_tools")
    await discordbot.load_extension("alttprbot_discord.cogs.role")
    await discordbot.load_extension("alttprbot_discord.cogs.sgdailies")
    await discordbot.load_extension("alttprbot_discord.cogs.tournament")
    await discordbot.load_extension("alttprbot_discord.cogs.voicerole")
    await discordbot.load_extension("alttprbot_discord.cogs.multiworld")
    await discordbot.load_extension("alttprbot_discord.cogs.generator")
    await discordbot.load_extension("alttprbot_discord.cogs.inquiry")

    if c.DEBUG:
        await discordbot.load_extension("alttprbot_discord.cogs.test")

    if importlib.util.find_spec('jishaku'):
        await discordbot.load_extension('jishaku')

    # if importlib.util.find_spec('sahasrahbot_private'):
    #     await discordbot.load_extension('sahasrahbot_private.stupid_memes')

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
        with push_scope() as scope:
            scope.set_tag("guild", ctx.guild.id if ctx.guild else "")
            scope.set_tag("channel", ctx.channel.id if ctx.channel else "")
            scope.set_tag("user", f"{ctx.author.name}#{ctx.author.discriminator}" if ctx.author else "")
            raise error_to_display


@discordbot.event
async def on_command(ctx):
    await ctx.message.add_reaction('⌚')


@discordbot.event
async def on_command_completion(ctx):
    await ctx.message.add_reaction('✅')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)

@discordbot.event
async def on_ready():
    await discordbot.tree.sync()

async def start_bot():
    await load_extensions()
    if c.DEBUG:
        discordbot.tree.copy_global_to(guild=discord.Object(id=508335685044928540)) # hard code the discord server id for now
    await discordbot.start(os.environ.get("DISCORD_TOKEN"))