import io
import json

import aiohttp
import discord
import yaml
from discord.ext import commands
from z3rsramr import parse_sram

import pyz3r
from alttprbot.alttprgen.mystery import (generate_random_game,
                                         generate_test_game)
from alttprbot.alttprgen.preset import get_preset, fetch_preset, generate_preset
from alttprbot.alttprgen.spoilers import generate_spoiler_game
from alttprbot.database import audit, config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import alttpr

from ..util import checks

# from config import Config as c



class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def goalstring(self, ctx, hash_id):
        seed = await alttpr(hash_id=hash_id)
        await ctx.send(
            f"goal string: `{seed.generated_goal}`\n"
            f"file select code: {seed.build_file_select_code(emojis=self.bot.emojis)}"
        )

    @commands.group(
        brief='Generate a race preset.',
        help='Generate a race preset.  Find a list of presets at https://l.synack.live/presets',
        invoke_without_command=True,
        aliases=['racepreset', 'race']
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def preset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="off")
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @preset.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def preset_custom(self, ctx, tournament: bool = True):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            preset_dict = yaml.safe_load(content)
            seed = await generate_preset(preset_dict, preset='custom', spoilers="off", tournament=True)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.group(
        brief='Generate a preset without the race flag enabled.',
        help='Generate a preset without the race flag enabled.  Find a list of presets at https://l.synack.live/presets',
        invoke_without_command=True,
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def nonracepreset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="on", tournament=False)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @nonracepreset.command(
        name='custom',
        brief='Generate a custom preset.',
        help='Generate a custom preset.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def nonracepreset_custom(self, ctx, tournament: bool = True):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            preset_dict = yaml.safe_load(content)
            seed = await generate_preset(preset_dict, preset='custom', spoilers="on", tournament=True)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        brief='Generate a spoiler game.',
        help='Generate a spoiler game.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler(self, ctx, preset):
        seed, preset_dict, spoiler_log_url = await generate_spoiler_game(preset)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(f'Spoiler log <{spoiler_log_url}>', embed=embed)

    @commands.group(
        brief='Generate a game with randomized settings.',
        help='Generate a game with randomized settings.  Find a list of weights at https://l.synack.live/weights',
        invoke_without_command=True,
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        await randomgame(ctx=ctx, weightset=weightset, tournament=tournament, spoilers="off", festive=False)

    @random.command(
        name='custom',
        brief='Generate a mystery game with custom weights.',
        help='Generate a mystery game with custom weights.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def random_custom(self, ctx, tournament: bool = True):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            weights = yaml.safe_load(content)
            await randomgame(ctx=ctx, weights=weights, weightset='custom', tournament=tournament, spoilers="off", festive=False)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    @commands.group(
        brief='Generate a mystery game.',
        help='Generate a mystery game.  Find a list of weights at https://l.synack.live/weights',
        invoke_without_command=True,
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=True, spoilers="mystery", festive=False)

    @mystery.command(
        name='custom',
        brief='Generate a mystery game with custom weights.',
        help='Generate a mystery game with custom weights.  This file should be attached to the message.'
    )
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def mystery_custom(self, ctx):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            weights = yaml.safe_load(content)
            await randomgame(ctx=ctx, weights=weights, weightset='custom', tournament=True, spoilers="mystery", festive=False)
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

    @commands.command(
        brief='Generate a mystery game.',
        help='Generate a mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @commands.is_owner()
    async def mysterytest(self, ctx, weightset='bot_testing'):
        resp = await generate_test_game(weightset=weightset)
        await ctx.send(file=discord.File(io.StringIO(json.dumps(resp, indent=4)), filename=f"{weightset}.txt"))

    @commands.command(
        brief='Verify a game was generated by SahasrahBot.',
        help='Verify a game was generated by SahasrahBot.\nThis can be useful for checking that customizer games are not a plando or something like that if you accept viewer games as a streamer.'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def verifygame(self, ctx, hash_id):
        result = await audit.get_generated_game(hash_id)
        if result:
            await ctx.send((
                f"{hash_id} was generated by SahasrahBot.\n\n"
                f"**Randomizer:** {result['randomizer']}\n"
                f"**Game Type:** {result['gentype']}\n"
                f"**Game Option:** {result['genoption']}\n\n"
                f"**Permalink:** <{result['permalink']}>"
            ))
        else:
            await ctx.send("That game was not generated by SahasrahBot.")

    @commands.command(
        brief='Get changes in retrieved game vs. baseline settings.'
    )
    @commands.is_owner()
    async def mysteryspoiler(self, ctx, hash_id):
        result = await audit.get_generated_game(hash_id)
        if not result:
            raise SahasrahBotException('That game was not generated by this bot.')

        if not result['randomizer'] == 'alttpr':
            raise SahasrahBotException('That is not an alttpr game.')
        if not result['gentype'] == 'mystery':
            raise SahasrahBotException('That is not a mystery game.')

        settings = json.loads(result['settings'])

        await ctx.send(file=discord.File(io.StringIO(json.dumps(settings, indent=4)), filename=f"{hash_id}.txt"))


    @commands.group(
        brief='Generate a festive game with randomized settings.',
        help='Generate a festive game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @checks.restrict_command_globally('FestiveMode')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def festiverandom(self, ctx, weightset='weighted', tournament: bool = True):
        await randomgame(ctx=ctx, weightset=weightset, tournament=tournament, spoilers="off", festive=True)

    @commands.group(
        brief='Generate a festive mystery game.',
        help='Generate a festive mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @checks.restrict_command_globally('FestiveMode')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def festivemystery(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=True, spoilers="mystery", festive=True)

    @commands.command(hidden=True, aliases=['festives'])
    async def festive(self, ctx):
        if await config.get(0, 'FestiveMode') == "true":
            embed = discord.Embed(
                title='Festive Randomizer Information',
                description='Latest details of any upcoming festive randomizers.',
                color=discord.Color.green()
            )
            embed.add_field(name="Christmas Festive 2019", value="https://alttpr.com/special")
        else:
            embed = discord.Embed(
                title='Festive Randomizer Information',
                description='Latest details of any upcoming festive randomizers.',
                color=discord.Color.red()
            )
            embed.set_image(
                url='https://cdn.discordapp.com/attachments/307860211333595146/654123045375442954/unknown.png')
        await ctx.send(embed=embed)

    @commands.command()
    async def alttprstats(self, ctx, raw: bool = False):
        if ctx.message.attachments:
            sram = await ctx.message.attachments[0].read()
            parsed = parse_sram(sram)
            if raw:
                await ctx.send(
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
                    seed = await alttpr(hash_id=parsed.get('hash id', 'none'))
                    embed.add_field(name='File Select Code', value=seed.build_file_select_code(
                        emojis=ctx.bot.emojis
                    ), inline=False)
                    embed.add_field(name='Permalink', value=seed.url, inline=False)

                await ctx.send(embed=embed)
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
            await ctx.send(
                file=discord.File(
                    io.StringIO(yaml.dump(preset_dict)),
                    filename=f"output.yaml"
                )
            )
        else:
            raise SahasrahBotException("You must supply a valid yaml file.")

async def randomgame(ctx, weightset=None, weights=None, tournament=True, spoilers="off", festive=False):
    seed = await generate_random_game(
        weightset=weightset,
        weights=weights,
        tournament=tournament,
        spoilers=spoilers,
        festive=festive
    )
    embed = await seed.embed(emojis=ctx.bot.emojis, name="Mystery Game")
    await ctx.send(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
