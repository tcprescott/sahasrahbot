from discord.ext import commands

from alttprbot.services import guild_config


def restrict_to_channels_by_guild_config(parameter, default=True):
    async def predicate(ctx):
        if ctx.guild is None:
            return True

        channels = await guild_config.get_list(ctx.guild.id, parameter)
        if channels is None:
            return default

        return ctx.channel.name in channels

    return commands.check(predicate)


def restrict_command_globally(parameter, default=False):
    async def predicate(ctx):
        value = await guild_config.get(0, parameter)
        if value is None:
            return default

        return value == 'true'

    return commands.check(predicate)


def has_any_channel(*channels):
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        return ctx.channel and ctx.channel.name in channels

    return commands.check(predicate)


def has_any_channel_id(*channels):
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        return ctx.channel and ctx.channel.id in channels

    return commands.check(predicate)
