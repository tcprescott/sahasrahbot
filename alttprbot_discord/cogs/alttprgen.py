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

    @commands.command()
    @commands.is_owner()
    async def goalstring(self, ctx, hash_id):
        seed = await ALTTPRDiscord.retrieve(hash_id=hash_id)
        await ctx.reply(
            f"goal string: `{seed.generated_goal}`\n"
            f"file select code: {seed.build_file_select_code(emojis=self.bot.emojis)}"
        )

    @commands.group(
        brief='Generate a race preset.',
        help='Generate a race preset.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        aliases=['racepreset', 'preset', 'quickswaprace']
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def race(self, ctx, preset, hints=False):
        # seed, _ = await get_preset(preset, hints=hints, spoilers="off", allow_quickswap=True)
        seed = await generator.ALTTPRPreset(preset).generate(hints=hints, spoilers="off", allow_quickswap=True)

        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)
        await ctx.reply("Please consider using the `/alttpr preset` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @race.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def race_custom(self, ctx):
        await self.customgame(ctx, spoilers="off", tournament=True, allow_quickswap=True)

    @commands.group(
        brief='Generate a non-quickswap race.',
        help='Generate a non-quickswap race.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def noqsrace(self, ctx, preset, hints=False):
        # seed, _ = await get_preset(preset, hints=hints, spoilers="off", tournament=True, allow_quickswap=False)
        seed = await generator.ALTTPRPreset(preset).generate(hints=hints, spoilers="off", tournament=True, allow_quickswap=False)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)
        await ctx.reply("Please consider using the `/alttpr preset` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @noqsrace.command(
        name='custom',
        brief='Generate a non-quickswap race custom preset.',
        help='Generate a non-quickswap race custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def noqsrace_custom(self, ctx):
        await self.customgame(ctx, spoilers="off", tournament=True, allow_quickswap=False)
        await ctx.reply("Please consider using the `/alttpr custompreset` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @commands.group(
        brief='Generate a preset without the race flag enabled.',
        help='Generate a preset without the race flag enabled.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        aliases=['nonracepreset']
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def norace(self, ctx, preset, hints=False):
        # seed, _ = await get_preset(preset, hints=hints, spoilers="on", tournament=False)
        seed = await generator.ALTTPRPreset(preset).generate(hints=hints, spoilers="on", tournament=False)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)
        await ctx.reply("Please consider using the `/alttpr preset` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @norace.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def norace_custom(self, ctx):
        await self.customgame(ctx, spoilers="on", tournament=False)
        await ctx.reply("Please consider using the `/alttpr custompreset` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @commands.group(
        brief='Generate a spoiler game.',
        help='Generate a spoiler game.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler(self, ctx, preset):
        spoiler = await generate_spoiler_game(preset)

        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Spoiler Log URL",
                              value=spoiler.spoiler_log_url, inline=False)
        await ctx.reply(embed=embed)
        await ctx.reply("Please consider using the `/alttpr spoiler` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @spoiler.command(
        name='custom',
        brief='Generate a custom spoiler race.',
        help='Generate a custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler_custom(self, ctx):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            spoiler = await generate_spoiler_game_custom(content)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")
        embed = await spoiler.seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Spoiler Log URL",
                              value=spoiler.spoiler_log_url, inline=False)
        await ctx.reply(embed=embed)
        await ctx.reply("Please consider using the `/alttpr customspoiler` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @commands.group(
        brief='Generate a game with randomized settings.',
        help='Generate a game with randomized settings.  Find a list of weights at https://sahasrahbot.synack.live/mystery.html',
        invoke_without_command=True,
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=False, spoilers="on")
        await ctx.reply("Please consider using the `/alttpr mystery` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @random.command(
        name='custom',
        brief='Generate a mystery game with custom weights.',
        help='Generate a mystery game with custom weights.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def random_custom(self, ctx):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            weights = yaml.safe_load(content)
            await randomgame(ctx=ctx, weights=weights, weightset='custom', tournament=False, spoilers="on")
            await ctx.reply("Please consider using the `/alttpr custommystery` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    @commands.group(
        brief='Generate a mystery game.',
        help='Generate a mystery game.  Find a list of weights at https://sahasrahbot.synack.live/mystery.html',
        invoke_without_command=True,
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=True, spoilers="mystery")
        await ctx.reply("Please consider using the `/alttpr mystery` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")

    @mystery.command(
        name='custom',
        brief='Generate a mystery game with custom weights.',
        help='Generate a mystery game with custom weights.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def mystery_custom(self, ctx):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            weights = yaml.safe_load(content)
            await randomgame(ctx=ctx, weights=weights, weightset='custom', tournament=True, spoilers="mystery")
            await ctx.reply("Please consider using the `/alttpr custommystery` slash command, as the command you invoked will be removed soon from SahasrahBot.  Thanks!")
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    @commands.command(hidden=True, aliases=['festives'])
    async def festive(self, ctx):
        if await config.get(0, 'FestiveMode') == "true":
            embed = discord.Embed(
                title='Festive Randomizer Information',
                description='Latest details of any upcoming festive randomizers.',
                color=discord.Color.green()
            )
            embed.add_field(name="Fall Festive 2020",
                            value="https://alttpr.com/festive/en/randomizer")
        else:
            embed = discord.Embed(
                title='Festive Randomizer Information',
                description='Latest details of any upcoming festive randomizers.',
                color=discord.Color.red()
            )
            embed.set_image(
                url='https://cdn.discordapp.com/attachments/307860211333595146/654123045375442954/unknown.png')
        await ctx.reply(embed=embed)

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

    async def customgame(self, ctx, spoilers="off", tournament=True, allow_quickswap=False):
        namespace = await generator.create_or_retrieve_namespace(ctx.author.id, ctx.author.name)

        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            data = await generator.ALTTPRPreset.custom(content, f"{namespace.name}/latest")
            await data.save()
            seed = await data.generate(spoilers=spoilers, tournament=tournament, allow_quickswap=allow_quickswap)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

        embed: discord.Embed = await seed.embed(emojis=self.bot.emojis)
        embed.add_field(name="Saved as preset!", value=f"You can generate this preset again by using the preset name of `{namespace.name}/latest`\n\nExample: `$norace {namespace.name}/latest`", inline=False)
        await ctx.reply(embed=embed)


async def randomgame(ctx, weightset=None, weights=None, tournament=True, spoilers="off"):
    if weights:
        namespace = await generator.create_or_retrieve_namespace(ctx.author.id, ctx.author.name)
        data = await generator.ALTTPRMystery.custom_from_dict(weights, f"{namespace.name}/latest")
        await data.save()
    else:
        data = generator.ALTTPRMystery(weightset)

    mystery = await data.generate(spoilers=spoilers, tournament=tournament)

    embed = await mystery.seed.embed(emojis=ctx.bot.emojis, name="Mystery Game")

    if mystery.custom_instructions:
        embed.insert_field_at(0, name="Custom Instructions", value=mystery.custom_instructions, inline=False)

    if weights:
        embed.add_field(name="Saved as custom weightset!", value=f"You can generate this weightset again by using the weightset name of `{namespace.name}/latest`.\n\nExample: `$mystery {namespace.name}/latest`", inline=False)

    await ctx.reply(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
