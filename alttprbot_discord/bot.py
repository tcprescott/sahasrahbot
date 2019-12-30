import importlib

import discord
from discord.ext import commands

from alttprbot.database import config


async def determine_prefix(bot, message):
    if message.guild is None:
        return "$"

    prefix = await config.get_parameter(message.guild.id, "CommandPrefix")

    if prefix is None:
        return "$"
    else:
        return prefix['value']


discordbot = commands.Bot(
    command_prefix=determine_prefix,
)

# discordbot.load_extension("alttprbot_discord.cogs.audit")
discordbot.load_extension("alttprbot_discord.cogs.admin")
discordbot.load_extension("alttprbot_discord.cogs.alttprgen")
discordbot.load_extension("alttprbot_discord.cogs.bontamw")
discordbot.load_extension("alttprbot_discord.cogs.daily")
discordbot.load_extension("alttprbot_discord.cogs.misc")
discordbot.load_extension("alttprbot_discord.cogs.moderation")
discordbot.load_extension("alttprbot_discord.cogs.nickname")
discordbot.load_extension("alttprbot_discord.cogs.role")
discordbot.load_extension("alttprbot_discord.cogs.smz3gen")
discordbot.load_extension("alttprbot_discord.cogs.tournament")
# discordbot.load_extension("alttprbot_discord.cogs.tourneyqualifier")
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
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(error)
        await ctx.message.add_reaction(riplink)
    else:
        await ctx.send(error.original)
        await ctx.message.add_reaction(riplink)
        raise error.original


@discordbot.event
async def on_command(ctx):
    await ctx.message.add_reaction('⌚')


@discordbot.event
async def on_command_completion(ctx):
    await ctx.message.add_reaction('✅')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)


@discordbot.event
async def on_message(message):
    if discordbot.user in message.mentions:
        emoji = discord.utils.get(discordbot.emojis, name='SahasrahBot')
        if emoji:
            await message.add_reaction(emoji)

    # override discord.py's process_commands coroutine in the commands.Bot class
    # this allows SpeedGamingBot to issue commands to SahasrahBot
    if message.author.bot and not message.author.id == 344251539931660288:
        return

    ctx = await discordbot.get_context(message)
    await discordbot.invoke(ctx)
