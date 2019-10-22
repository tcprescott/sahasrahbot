import asyncio
import discord
from discord.ext import commands
import importlib

# from alttprbot import reactionrole
from alttprbot.util import orm

from config import Config as c

discordbot = commands.Bot(
    command_prefix="$",
)

discordbot.load_extension("alttprbot.cogs.admin")
# discordbot.load_extension("alttprbot.cogs.audit")
discordbot.load_extension("alttprbot.cogs.moderation")
discordbot.load_extension("alttprbot.cogs.role")
discordbot.load_extension("alttprbot.cogs.misc")
discordbot.load_extension("alttprbot.cogs.daily")
discordbot.load_extension("alttprbot.cogs.voicerole")
discordbot.load_extension("alttprbot.cogs.alttprgen")
discordbot.load_extension("alttprbot.cogs.smz3gen")
discordbot.load_extension("alttprbot.cogs.tournament")

if importlib.util.find_spec('jishaku'):
    discordbot.load_extension('jishaku')

if not c.DEBUG:
    @discordbot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
        if isinstance(error, commands.errors.MissingPermissions):
            await ctx.message.add_reaction('🚫')
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(error)
            await ctx.message.add_reaction('👎')
        else:
            await ctx.send(error)
            await ctx.message.add_reaction('👎')
        await ctx.message.remove_reaction('⌚', ctx.bot.user)


@discordbot.event
async def on_command(ctx):
    await ctx.message.add_reaction('⌚')


@discordbot.event
async def on_command_completion(ctx):
    await ctx.message.add_reaction('👍')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)


@discordbot.event
async def on_message(message):
    if discordbot.user in message.mentions:
        emoji = discord.utils.get(discordbot.emojis, name='SahasrahBot')
        if emoji:
            await message.add_reaction(emoji)

    await discordbot.process_commands(message)

# @discordbot.check
# async def globally_block_dms(ctx):
#     if ctx.guild is None:
#         return False
#     else:
#         return True

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    loop.create_task(discordbot.start(c.DISCORD_TOKEN))
    loop.run_forever()
