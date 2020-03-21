import io
import json

import aiohttp
import discord
from discord.ext import commands
from z3rsramr import parse_sram

import pyz3r
from alttprbot.alttprgen.mystery import (generate_random_game,
                                         generate_test_game)
from alttprbot.alttprgen.preset import get_preset
from alttprbot.alttprgen.spoilers import generate_spoiler_game
from alttprbot.database import audit, config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import build_file_select_code

from ..util import checks
from ..util.alttpr_discord import alttpr

# from config import Config as c



class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief='Generate a customizer game.',
        help='Generate a customizer game using a customizer save file attached to the message.'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def custom(self, ctx, tournament: bool = True):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise SahasrahBotException('File should have a .json extension.')
        except IndexError as err:
            raise SahasrahBotException('You must attach a customizer save json file.') from err

        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = pyz3r.customizer.convert2settings(
            customizer_settings, tournament=tournament)

        seed = await alttpr(customizer=True, settings=settings)

        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        brief='Generate a race preset.',
        help='Generate a race preset.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def preset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="off")
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        brief='Generate a preset without the race flag enabled.',
        help='Generate a preset without the race flag enabled.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def nonracepreset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="on", tournament=False)
        if not seed:
            raise SahasrahBotException(
                'Could not generate game.  Maybe preset does not exist?')
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

    @commands.command(
        brief='Generate a game with randomized settings.',
        help='Generate a game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        await randomgame(ctx=ctx, weightset=weightset, tournament=tournament, spoilers="off", festive=False)

    @commands.command(
        brief='Generate a mystery game.',
        help='Generate a mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=True, spoilers="mystery", festive=False)

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


    @commands.command(
        brief='Generate a festive game with randomized settings.',
        help='Generate a festive game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @checks.restrict_command_globally('FestiveMode')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def festiverandom(self, ctx, weightset='weighted', tournament: bool = True):
        await randomgame(ctx=ctx, weightset=weightset, tournament=tournament, spoilers="off", festive=True)

    @commands.command(
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
    async def alttprstats(self, ctx):
        if ctx.message.attachments:
            sram = await ctx.message.attachments[0].read()
            parsed = parse_sram(sram)
            embed = discord.Embed(
                title=f"ALTTPR Stats for \"{parsed.get('filename', '').strip()}\"",
                description=f"Collection Rate {parsed.get('collection rate')}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Time",
                value=(
                    f"Total Time: {parsed.get('total time', None)}\n"
                    f"Lag Time: {parsed.get('lag time', None)}\n"
                    f"Menu Time: {parsed.get('menu time', None)}\n\n"
                    f"First Sword: {parsed.get('first sword', None)}\n"
                    f"Flute Found: {parsed.get('flute found', None)}\n"
                    f"Mirror Found: {parsed.get('mirror found', None)}\n"
                    f"Boots Found: {parsed.get('boots found', None)}\n"
                ),
                inline=False
            )
            embed.add_field(
                name="Important Stats",
                value=(
                    f"Bonks: {parsed.get('bonks', None)}\n"
                    f"Deaths: {parsed.get('deaths', None)}\n"
                    f"Revivals: {parsed.get('fairy revivals', None)}\n"
                    f"Overworld Mirrors: {parsed.get('overworld mirrors', None)}\n"
                    f"Rupees Spent: {parsed.get('rupees spent', None)}\n"
                    f"Save and Quits: {parsed.get('save and quits', None)}\n"
                    f"Screen Transitions: {parsed.get('screen transitions', None)}\n"
                    f"Times Fluted: {parsed.get('times fluted', None)}\n"
                    f"Underworld Mirrors: {parsed.get('underworld mirrors', None)}\n"
                )
            )
            embed.add_field(
                name="Misc Stats",
                value=(
                    f"Swordless Bosses: {parsed.get('swordless bosses', None)}\n"
                    f"Fighter Sword Bosses: {parsed.get('fighter sword bosses', None)}\n"
                    f"Master Sword Bosses: {parsed.get('master sword bosses', None)}\n"
                    f"Tempered Sword Bosses: {parsed.get('tempered sword bosses', None)}\n"
                    f"Golden Sword Bosses: {parsed.get('golden sword bosses', None)}\n\n"
                    f"Heart Containers: {parsed.get('heart containers', None)}\n"
                    f"Heart Containers: {parsed.get('heart pieces', None)}\n"
                    f"Mail Upgrade: {parsed.get('mails', None)}\n"

                )
            )
            if not parsed.get('hash id', 'none') == 'none':
                seed = await pyz3r.alttpr(hash_id=parsed.get('hash id', 'none'))
                embed.add_field(name='File Select Code', value=await build_file_select_code(
                    code=await seed.code(),
                    emojis=ctx.bot.emojis
                ), inline=False)
                embed.add_field(name='Permalink', value=seed.url, inline=False)

            await ctx.send(embed=embed)
        else:
            raise SahasrahBotException("You must attach an SRAM file.")

async def randomgame(ctx, weightset, tournament=True, spoilers="off", festive=False):
    if weightset == "custom" and not ctx.message.attachments:
        raise SahasrahBotException(
            'You must attach a file when specifying a custom weightset.')
    if weightset == "custom" and not ctx.message.attachments[0].filename.endswith('.yaml'):
        raise SahasrahBotException('File should have a .yaml extension.')
    elif not weightset == "custom" and ctx.message.attachments:
        raise SahasrahBotException(
            'If you\'re intending to use a custom weightset, please specify the weightset as "custom".')

    seed = await generate_random_game(
        weightset=weightset,
        tournament=tournament,
        spoilers=spoilers,
        custom_weightset_url=ctx.message.attachments[0].url if weightset == "custom" else None,
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
