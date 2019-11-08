import asyncio
import discord
from discord.ext import commands
import importlib
import traceback

# from alttprbot import reactionrole
from alttprbot.util import orm
from alttprbot.api.app import app

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
discordbot.load_extension("alttprbot.cogs.srl")

if importlib.util.find_spec('jishaku'):
    discordbot.load_extension('jishaku')


@discordbot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction('⌚', ctx.bot.user)
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
        traceback_data = ''.join(traceback.format_exception(type(error), error, error.__traceback__, 1))
        formatted_traceback = f'User: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})\nGuild: {ctx.guild.name} ({ctx.guild.id})\nChannel: {ctx.channel.name} ({ctx.channel.id})\nMessage: {ctx.message.clean_content}\n```python\n{traceback_data}```'
        if c.DEBUG:
            await ctx.send(formatted_traceback)
        else:
            app = await ctx.bot.application_info()
            await app.owner.send(formatted_traceback)
            await ctx.send(error)
        
        await ctx.message.add_reaction('👎')


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
    loop.create_task(app.run(host='127.0.0.1', port=5001, loop=loop))
    loop.run_forever()
