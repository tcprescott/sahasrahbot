from discord.ext import commands

def has_any_channel(*channels):
    async def predicate(ctx):
        if ctx.guild is None: return False
        return ctx.channel and ctx.channel.name in channels
    return commands.check(predicate)