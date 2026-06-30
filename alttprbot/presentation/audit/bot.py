import io
import logging
import asyncio

import discord
from discord.ext import commands
from discord_sentry_reporting import use_sentry

import config
from alttprbot.services import GuildConfigService


async def determine_prefix(bot, message):
    if message.guild is None:
        return "$"

    prefix = await GuildConfigService().get(message.guild.id, "CommandPrefix", "$")
    return prefix


discordbot = commands.Bot(
    command_prefix=determine_prefix,
    allowed_mentions=discord.AllowedMentions(
        everyone=False,
        users=True,
        roles=False
    ),
    intents=discord.Intents.all(),
    debug_guild=508335685044928540 if config.DEBUG else None
)

if config.SENTRY_URL:
    use_sentry(discordbot, dsn=config.SENTRY_URL)


async def load_extensions():
    await discordbot.load_extension("alttprbot.presentation.audit.cogs.audit")
    await discordbot.load_extension("alttprbot.presentation.audit.cogs.moderation")


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
async def on_ready():
    await discordbot.tree.sync()


async def start_bot():
    await load_extensions()
    if config.DEBUG:
        discordbot.tree.copy_global_to(
            guild=discord.Object(id=508335685044928540))  # hard code the discord server id for now
    try:
        await discordbot.start(config.AUDIT_DISCORD_TOKEN)
    except asyncio.CancelledError:
        if not discordbot.is_closed():
            await discordbot.close()
        raise


async def stop_bot():
    if not discordbot.is_closed():
        await discordbot.close()
