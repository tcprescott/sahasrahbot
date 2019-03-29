import asyncio
import discord
from discord.ext.commands import commands

discordbot = commands.Bot(
    command_prefix="$",
)

@discordbot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.message.add_reaction('🚫')
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(error)
        await ctx.message.add_reaction('👎')
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.errors.CommandOnCooldown):
        pass
    else:
        await ctx.send(error)
        await ctx.message.add_reaction('👎')
    await ctx.message.remove_reaction('⌚',ctx.bot.user)

@discordbot.check
async def globally_block_dms(ctx):
    if ctx.guild is None and not ctx.invoked_with in ['practice']:
        return False
    else:
        return True

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(discordbot.start(config['discord_token']))
    loop.create_task(ircbot.connect())
    loop.run_forever()
