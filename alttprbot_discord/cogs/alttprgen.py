import io
import json

import aiohttp
import discord
import yaml
from discord.ext import commands
from z3rsramr import parse_sram  # pylint: disable=no-name-in-module

import pyz3r
from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.alttprgen.spoilers import generate_spoiler_game, generate_spoiler_game_custom
from alttprbot.database import config  # TODO switch to ORM
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord

from ..util import checks


class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        brief='Generate a race preset.',
        help='Generate a race preset.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        aliases=['racepreset', 'preset', 'quickswaprace'],
        hidden=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def race(self, ctx, preset, hints=False):
        await ctx.reply("This command has been replaced with `/alttpr preset` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @race.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.',
        hidden=True
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def race_custom(self, ctx):
        await ctx.reply("This command has been replaced with `/alttpr custompreset` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @commands.group(
        brief='Generate a non-quickswap race.',
        help='Generate a non-quickswap race.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        hidden=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def noqsrace(self, ctx, preset, hints=False):
        await ctx.reply("This command has been replaced with `/alttpr preset` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @noqsrace.command(
        name='custom',
        brief='Generate a non-quickswap race custom preset.',
        help='Generate a non-quickswap race custom preset.  This file should be attached to the message.',
        hidden=True
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def noqsrace_custom(self, ctx):
        await ctx.reply("This command has been replaced with `/alttpr custompreset` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @commands.group(
        brief='Generate a preset without the race flag enabled.',
        help='Generate a preset without the race flag enabled.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        aliases=['nonracepreset'],
        hidden=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def norace(self, ctx, preset, hints=False):
        await ctx.reply("This command has been replaced with `/alttpr preset` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @norace.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.',
        hidden=True
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def norace_custom(self, ctx):
        await ctx.reply("This command has been replaced with `/alttpr custompreset` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @commands.group(
        brief='Generate a spoiler game.',
        help='Generate a spoiler game.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        hidden=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler(self, ctx, preset):
        await ctx.reply("This command has been replaced with `/alttpr spoiler` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @spoiler.command(
        name='custom',
        brief='Generate a custom spoiler race.',
        help='Generate a custom preset.  This file should be attached to the message.',
        hidden=True
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler_custom(self, ctx):
        await ctx.reply("This command has been replaced with `/alttpr customspoiler` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @commands.group(
        brief='Generate a game with randomized settings.',
        help='Generate a game with randomized settings.  Find a list of weights at https://sahasrahbot.synack.live/mystery.html',
        invoke_without_command=True, ,
        hidden=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted'):
        await ctx.reply("This command has been replaced with `/alttpr mystery` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @random.command(
        name='custom',
        brief='Generate a mystery game with custom weights.',
        help='Generate a mystery game with custom weights.  This file should be attached to the message.',
        hidden=True
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def random_custom(self, ctx):
        await ctx.reply("This command has been replaced with `/alttpr custommystery` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @commands.group(
        brief='Generate a mystery game.',
        help='Generate a mystery game.  Find a list of weights at https://sahasrahbot.synack.live/mystery.html',
        invoke_without_command=True,
        hidden=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted'):
        await ctx.reply("This command has been replaced with `/alttpr mystery` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @mystery.command(
        name='custom',
        brief='Generate a mystery game with custom weights.',
        help='Generate a mystery game with custom weights.  This file should be attached to the message.',
        hidden=True
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def mystery_custom(self, ctx):
        await ctx.reply("This command has been replaced with `/alttpr custommystery` slash command.\nThis \"$\" command is no longer available.  Please contact Synack if you have any issues.")

    @commands.command(hidden=True)
    async def alttprstats(self, ctx):
        await ctx.reply("This command is currently disabled.  Please use the `/alttprutil stats` command instead.")

    @commands.command(hidden=True)
    async def convertcustomizer(self, ctx):
        await ctx.reply("This command is currently disabled.  Please use the `/alttprutil convertcustomizer` command instead.")

    @commands.command(hidden=True)
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def kisspriest(self, ctx, count=10):
        await ctx.reply("Please use the new slash command \"/alttpr kisspriest\".")

    @commands.command(hidden=True)
    async def savepreset(self, ctx, preset):
        await ctx.reply("This command is currently disabled.  Please use the `/alttprutil savepreset` command instead.")


def setup(bot):
    bot.add_cog(AlttprGen(bot))
