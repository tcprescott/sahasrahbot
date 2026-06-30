from discord.ext import commands

from alttprbot.services import GuildConfigService


def restrict_to_channels_by_guild_config(parameter, default=True):
    async def predicate(ctx):
        if ctx.guild is None:
            return True

        value = await GuildConfigService().get(ctx.guild.id, parameter)
        if value is None:
            return default

        channels = value.split(',')
        if ctx.channel.name in channels:
            return True

        return False

    return commands.check(predicate)


def restrict_command_globally(parameter, default=False):
    async def predicate(ctx):
        value = await GuildConfigService().get(0, parameter)
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
