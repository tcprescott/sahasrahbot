import asyncio
import discord
from discord.ext import commands

from alttprbot import reactionrole
from alttprbot.util import orm

from config import Config

discordbot = commands.Bot(
    command_prefix="$",
)

discordbot.load_extension("alttprbot.cogs.admin")
discordbot.load_extension("alttprbot.cogs.role")

@discordbot.command()
async def test(ctx, emoji):
    await reactionrole.create_role(12345,1,1234,'test',emoji)

@discordbot.command()
async def test2(ctx):
    roles = await reactionrole.get_group_roles(1,12345)
    print(roles)


# @discordbot.event
# async def on_command_error(ctx, error):
#     if isinstance(error, commands.CheckFailure):
#         await ctx.message.add_reaction('🚫')
#     elif isinstance(error, commands.errors.MissingRequiredArgument):
#         await ctx.send(error)
#         await ctx.message.add_reaction('👎')
#     elif isinstance(error, commands.CommandNotFound):
#         pass
#     elif isinstance(error, commands.errors.CommandOnCooldown):
#         pass
#     else:
#         await ctx.send(error)
#         await ctx.message.add_reaction('👎')
#     await ctx.message.remove_reaction('⌚',ctx.bot.user)

@discordbot.check
async def globally_block_dms(ctx):
    if ctx.guild is None and not ctx.invoked_with in ['practice']:
        return False
    else:
        return True

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    loop.create_task(discordbot.start(Config.DISCORD_TOKEN))
    loop.run_forever()
