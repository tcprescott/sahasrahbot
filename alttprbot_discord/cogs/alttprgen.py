import io
import json

import aiohttp
import discord
import yaml
from discord.ext import commands
from z3rsramr import parse_sram  # pylint: disable=no-name-in-module
from slugify import slugify

import pyz3r
from alttprbot import models
from pyz3r.ext.priestmode import create_priestmode
from alttprbot.alttprgen.mystery import generate_random_game
from alttprbot.alttprgen.generator import ALTTPRPreset
from alttprbot.alttprgen.spoilers import generate_spoiler_game, generate_spoiler_game_custom
from alttprbot.database import config
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
        seed = await ALTTPRPreset(preset).generate(hints=hints, spoilers="off", allow_quickswap=True)

        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)

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
        seed = await ALTTPRPreset(preset).generate(hints=hints, spoilers="off", tournament=True, allow_quickswap=False)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)

    @noqsrace.command(
        name='custom',
        brief='Generate a non-quickswap race custom preset.',
        help='Generate a non-quickswap race custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def noqsrace_custom(self, ctx):
        await self.customgame(ctx, spoilers="off", tournament=True, allow_quickswap=False)

    @commands.group(
        brief='Generate a preset without the race flag enabled.',
        help='Generate a preset without the race flag enabled.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True,
        aliases=['nonracepreset']
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def norace(self, ctx, preset, hints=False):
        # seed, _ = await get_preset(preset, hints=hints, spoilers="on", tournament=False)
        seed = await ALTTPRPreset(preset).generate(hints=hints, spoilers="on", tournament=False)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.reply(embed=embed)

    @norace.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def norace_custom(self, ctx):
        await self.customgame(ctx, spoilers="on", tournament=True)

    @commands.group(
        brief='Generate a spoiler game.',
        help='Generate a spoiler game.  Find a list of presets at https://sahasrahbot.synack.live/presets.html',
        invoke_without_command=True
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler(self, ctx, preset):
        seed, _, spoiler_log_url = await generate_spoiler_game(preset)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Spoiler Log URL",
                              value=spoiler_log_url, inline=False)
        await ctx.reply(embed=embed)

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
            preset_dict = yaml.safe_load(content)
            seed, _, spoiler_log_url = await generate_spoiler_game_custom(preset_dict)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")
        embed = await seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Spoiler Log URL",
                              value=spoiler_log_url, inline=False)
        await ctx.reply(embed=embed)

    @commands.command(
        brief='Generate a progression spoiler game.',
        help='Generate a progression spoiler game.  Find a list of presets at https://sahasrahbot.synack.live/presets.html'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def progression(self, ctx, preset):
        seed, _, spoiler_log_url = await generate_spoiler_game(preset, spoiler_type='progression')
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        embed.insert_field_at(0, name="Progression Spoiler Log URL",
                              value=spoiler_log_url, inline=False)
        await ctx.reply(embed=embed)

    @commands.group(
        brief='Generate a game with randomized settings.',
        help='Generate a game with randomized settings.  Find a list of weights at https://sahasrahbot.synack.live/mystery.html',
        invoke_without_command=True,
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=False, spoilers="on")

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
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    @commands.command(
        brief='Verify a game was generated by SahasrahBot.',
        help='Verify a game was generated by SahasrahBot.\nThis can be useful for checking that customizer games are not a plando or something like that if you accept viewer games as a streamer.'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def verifygame(self, ctx, hash_id):
        result = await models.AuditGeneratedGames.filter(hash_id=hash_id).first().values()
        if result:
            await ctx.reply((
                f"{hash_id} was generated by SahasrahBot.\n\n"
                f"**Randomizer:** {result[0]['randomizer']}\n"
                f"**Game Type:** {result[0]['gentype']}\n"
                f"**Game Option:** {result[0]['genoption']}\n\n"
                f"**Permalink:** <{result[0]['permalink']}>"
            ))
        else:
            await ctx.reply("That game was not generated by SahasrahBot.")

    @commands.command(
        brief='Get changes in retrieved game vs. baseline settings.'
    )
    @commands.is_owner()
    async def mysteryspoiler(self, ctx, hash_id):
        result = await models.AuditGeneratedGames.filter(hash_id=hash_id).first().values()
        if not result:
            raise SahasrahBotException('That game was not generated by this bot.')

        if not result[0]['randomizer'] == 'alttpr':
            raise SahasrahBotException('That is not an alttpr game.')
        if not result[0]['gentype'] == 'mystery':
            raise SahasrahBotException('That is not a mystery game.')

        settings = result[0]['settings']

        await ctx.reply(file=discord.File(io.StringIO(json.dumps(settings, indent=4)), filename=f"{hash_id}.txt"))

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

    @commands.command()
    async def alttprstats(self, ctx, raw: bool = False):
        if ctx.message.attachments:
            sram = await ctx.message.attachments[0].read()
            parsed = parse_sram(sram)
            if raw:
                await ctx.reply(
                    file=discord.File(
                        io.StringIO(json.dumps(parsed, indent=4)),
                        filename=f"stats_{parsed['meta'].get('filename', 'alttpr').strip()}.txt"
                    )
                )
            else:
                embed = discord.Embed(
                    title=f"ALTTPR Stats for \"{parsed['meta'].get('filename', '').strip()}\"",
                    description=f"Collection Rate {parsed['stats'].get('collection rate')}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Time",
                    value=(
                        f"Total Time: {parsed['stats'].get('total time', None)}\n"
                        f"Lag Time: {parsed['stats'].get('lag time', None)}\n"
                        f"Menu Time: {parsed['stats'].get('menu time', None)}\n\n"
                        f"First Sword: {parsed['stats'].get('first sword', None)}\n"
                        f"Flute Found: {parsed['stats'].get('flute found', None)}\n"
                        f"Mirror Found: {parsed['stats'].get('mirror found', None)}\n"
                        f"Boots Found: {parsed['stats'].get('boots found', None)}\n"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="Important Stats",
                    value=(
                        f"Bonks: {parsed['stats'].get('bonks', None)}\n"
                        f"Deaths: {parsed['stats'].get('deaths', None)}\n"
                        f"Revivals: {parsed['stats'].get('faerie revivals', None)}\n"
                        f"Overworld Mirrors: {parsed['stats'].get('overworld mirrors', None)}\n"
                        f"Rupees Spent: {parsed['stats'].get('rupees spent', None)}\n"
                        f"Save and Quits: {parsed['stats'].get('save and quits', None)}\n"
                        f"Screen Transitions: {parsed['stats'].get('screen transitions', None)}\n"
                        f"Times Fluted: {parsed['stats'].get('times fluted', None)}\n"
                        f"Underworld Mirrors: {parsed['stats'].get('underworld mirrors', None)}\n"
                    )
                )
                embed.add_field(
                    name="Misc Stats",
                    value=(
                        f"Swordless Bosses: {parsed['stats'].get('swordless bosses', None)}\n"
                        f"Fighter Sword Bosses: {parsed['stats'].get('fighter sword bosses', None)}\n"
                        f"Master Sword Bosses: {parsed['stats'].get('master sword bosses', None)}\n"
                        f"Tempered Sword Bosses: {parsed['stats'].get('tempered sword bosses', None)}\n"
                        f"Golden Sword Bosses: {parsed['stats'].get('golden sword bosses', None)}\n\n"
                        f"Heart Containers: {parsed['stats'].get('heart containers', None)}\n"
                        f"Heart Containers: {parsed['stats'].get('heart pieces', None)}\n"
                        f"Mail Upgrade: {parsed['stats'].get('mails', None)}\n"
                        f"Bottles: {parsed['equipment'].get('bottles', None)}\n"
                        f"Silver Arrows: {parsed['equipment'].get('silver arrows', None)}\n"
                    )
                )
                if not parsed.get('hash id', 'none') == 'none':
                    seed = await ALTTPRDiscord.retrieve(hash_id=parsed.get('hash id', 'none'))
                    embed.add_field(name='File Select Code', value=seed.build_file_select_code(
                        emojis=ctx.bot.emojis
                    ), inline=False)
                    embed.add_field(name='Permalink', value=seed.url, inline=False)

                await ctx.reply(embed=embed)
        else:
            raise SahasrahBotException("You must attach an SRAM file.")

    @commands.command(
        brief='Make a SahasrahBot preset file from a customizer save.',
        help=(
            'Take a customizer settings save and create a SahasrahBot preset file from it.\n'
            'This can then be fed into SahasrahBot using the "$preset custom" command.\n\n'
        )
    )
    async def convertcustomizer(self, ctx):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            customizer_save = json.loads(content)
            settings = pyz3r.customizer.convert2settings(customizer_save)
            preset_dict = {
                'customizer': True,
                'goal_name': "REPLACE WITH SRL GOAL STRING",
                'randomizer': 'alttpr',
                'settings': settings
            }
            await ctx.reply(
                file=discord.File(
                    io.StringIO(yaml.dump(preset_dict)),
                    filename="output.yaml"
                )
            )
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    @commands.command(
        brief="Create a series of \"Kiss Priest\" games.",
        help=(
            'Create a series a \"Kiss Priest\" games.  This was created by hycutype.'
        )
    )
    @commands.cooldown(rate=15, per=900, type=commands.BucketType.user)
    async def kisspriest(self, ctx, count=10):
        if count > 10 or count < 1:
            raise SahasrahBotException(
                "Number of games generated must be between 1 and 10.")

        seeds = await create_priestmode(count=count, genclass=ALTTPRDiscord)
        embed = discord.Embed(
            title='Kiss Priest Games',
            color=discord.Color.blurple()
        )
        for idx, seed in enumerate(seeds):
            embed.add_field(
                name=seed.data['spoiler']['meta'].get('name', f"Game {idx}"),
                value=f"{seed.url}\n{seed.build_file_select_code(self.bot.emojis)}",
                inline=False
            )
        await ctx.reply(embed=embed)

    @commands.command()
    async def savepreset(self, ctx, preset):
        namespace, _ = await models.PresetNamespaces.get_or_create(discord_user_id=ctx.author.id, defaults={'name': slugify(ctx.author.name, max_length=20)})

        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            data = await ALTTPRPreset.custom(content, f"{namespace.name}/{preset}")
            await data.save()

            await ctx.send(f"Preset saved as {data.namespace}/{data.preset}")
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    async def customgame(self, ctx, spoilers="off", tournament=True, allow_quickswap=False):
        namespace, _ = await models.PresetNamespaces.get_or_create(discord_user_id=ctx.author.id, defaults={'name': slugify(ctx.author.name, max_length=20)})

        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            data = await ALTTPRPreset.custom(content, f"{namespace.name}/latest")
            await data.save()
            seed = await data.generate(spoilers=spoilers, tournament=tournament, allow_quickswap=allow_quickswap)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

        embed: discord.Embed = await seed.embed(emojis=self.bot.emojis)
        embed.add_field(name="Saved as preset!", value=f"You can generate this preset again by using the preset name of `{namespace.name}/latest`")
        await ctx.reply(embed=embed)


async def randomgame(ctx, weightset=None, weights=None, tournament=True, spoilers="off"):
    mystery = await generate_random_game(
        weightset=weightset,
        weights=weights,
        tournament=tournament,
        spoilers=spoilers
    )
    embed = await mystery.seed.embed(emojis=ctx.bot.emojis, name="Mystery Game")
    if mystery.custom_instructions:
        embed.insert_field_at(0, name="Custom Instructions", value=mystery.custom_instructions)
    await ctx.reply(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
