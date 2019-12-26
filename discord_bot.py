import asyncio
import discord
from discord.ext import commands
import importlib
import traceback

# from alttprbot import reactionrole
from alttprbot.util import orm
from alttprbot.api.app import app

from config import Config as c

# from dotenv import load_dotenv
# load_dotenv()

discordbot = commands.Bot(
    command_prefix="$",
)

# discordbot.load_extension("alttprbot.cogs.audit")
discordbot.load_extension("alttprbot.cogs.admin")
discordbot.load_extension("alttprbot.cogs.alttprgen")
discordbot.load_extension("alttprbot.cogs.bontamw")
discordbot.load_extension("alttprbot.cogs.daily")
discordbot.load_extension("alttprbot.cogs.misc")
discordbot.load_extension("alttprbot.cogs.moderation")
discordbot.load_extension("alttprbot.cogs.nickname")
discordbot.load_extension("alttprbot.cogs.role")
discordbot.load_extension("alttprbot.cogs.smz3gen")
discordbot.load_extension("alttprbot.cogs.tournament")
discordbot.load_extension("alttprbot.cogs.tourneyqualifier")
discordbot.load_extension("alttprbot.cogs.voicerole")

if importlib.util.find_spec('jishaku'):
    discordbot.load_extension('jishaku')

if not c.DEBUG:
    @discordbot.event
    async def on_command_error(ctx, error):
        riplink = discord.utils.get(ctx.bot.emojis, name='RIPLink')
        if riplink is None: riplink = '👎'

        await ctx.message.remove_reaction('⌚', ctx.bot.user)

        if isinstance(error, commands.CheckFailure):
            pass
        if isinstance(error, commands.errors.MissingPermissions):
            await ctx.message.add_reaction('🚫')
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(error)
            await ctx.message.add_reaction(riplink)
        else:
            await ctx.send(error)
            await ctx.message.add_reaction(riplink)


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


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    loop.create_task(discordbot.start(c.DISCORD_TOKEN))
    loop.create_task(app.run(host='127.0.0.1', port=5001, loop=loop))
    loop.run_forever()
