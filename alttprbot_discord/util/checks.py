from discord.ext import commands


def restrict_to_channels_by_guild_config(parameter, default=True):
    async def predicate(ctx):
        if ctx.guild is None:
            return True

        return default
    return commands.check(predicate)

def has_any_channel(*channels):
    async def predicate(ctx):
        if ctx.guild is None: return False
        return ctx.channel and ctx.channel.name in channels
    return commands.check(predicate)
