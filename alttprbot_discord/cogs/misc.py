import asyncio
import datetime
import random
import os
from aiocache import cached, Cache
import aiohttp

import discord
from discord import app_commands
from discord.ext import commands
import pytz
from pytz import UnknownTimeZoneError

from alttprbot.util.holyimage import HolyImage

# TODO: make work with discord.py 2.0


ALTTP_RANDOMIZER_SERVERS = list(map(int, os.environ.get("ALTTP_RANDOMIZER_SERVERS", "").split(',')))

WELCOME_MESSAGES = {
    'french': (
        'Bienvenue! Ce serveur discord est principalement en anglais.\n'
        'Vous trouverez un serveur en français en suivant https://discord.gg/9cWhQyw .\n'
        'Les membres de ce serveur se feront un plaisir de vous aider.\n\n'
        'Merci, et bienvenue encore une fois.'
    ),
    'spanish': (
        '¡Bienvenidos! Este servidor de Discord es principalmente de habla inglesa.'
        '¡No tengáis miedo, hay un servidor en Español que podéis encontrar en https://discord.gg/xyHxAFJ donde os pueden ayudar!\n\n'
        'Gracias y otra vez, bienvenidos.'
    ),
    'german': (
        'Willkommen! Auf diesem Server wird grundsätzlich in Englisch geschrieben.'
        'Aber keine Sorge, es gibt ebenfalls einen deutschen Discord-Server, der dir gerne in deiner Sprache helfen kann.'
        'Diesen findest du unter folgender Einladung https://discordapp.com/invite/5zuANcS . Dort gibt es alles - von Einsteigertipps bis zu Turnieren\n\n'
        'Vielen Dank und nochmals herzlich willkommen.'
    )
}

@cached(ttl=300, cache=Cache.MEMORY, key="holygamedefault")
async def holy_game_default(guild: discord.Guild):
    return await guild.config_get("HolyImageDefaultGame", "z3r")


@cached(ttl=300, cache=Cache.MEMORY, key="holyimages")
async def get_holy_images() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get('http://alttp.mymm1.com/holyimage/holyimages.json') as resp:
            return await resp.json()

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user in message.mentions:
            emoji = discord.utils.get(self.bot.emojis, name='SahasrahBot')
            if emoji:
                await asyncio.sleep(random.random()*5)
                await message.add_reaction(emoji)

    # TODO: make this app command guild-specific for ALTTP Randomizer
    @app_commands.command(description="Welcome messages for various languages.")
    @app_commands.describe(language="Choose a language for the welcome message.")
    @app_commands.choices(
        language=[
            app_commands.Choice(name=lang, value=lang) for lang in WELCOME_MESSAGES.keys()
        ]
    )
    async def welcome_cmd(self, interaction: discord.Interaction, language: str):
        await interaction.response.send_message(WELCOME_MESSAGES[language])

    # TODO: make this app command guild-specific for ALTTP Randomizer
    @app_commands.command(description="Get info about how to verify a ROM.")
    async def rom(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "If you need help verifying your legally-dumped Japanese version 1.0 A Link to the Past Game file needed to run ALTTPR, use this tool: <http://alttp.mymm1.com/game/checkcrc/>\n"
            "It can also help get the permalink page URL which has access to the Spoiler Log depending on the settings that were chosen. Not all games that are generated have access to the Spoiler Log.\n\n"
            "For legal reasons, we cannot provide help with finding this ROM online.  Please do not ask here for assistance with this.\n"
            "See <#543572578787393556> for details."
        )

    @app_commands.command(description="Retrieves a holy image from http://alttp.mymm1.com/holyimage/")
    @app_commands.describe(slug="The slug of the holy image to get.", game="The game to get the holy image from.")
    async def holyimage(
        self,
        interaction: discord.Interaction,
        slug: str,
        game: str = None
    ):
        if game is None:
            if interaction.guild is None:
                game = "z3r"
            else:
                game = await interaction.guild.config_get("HolyImageDefaultGame", "z3r")

        holyimage = await HolyImage.construct(slug=slug, game=game)

        await interaction.response.send_message(embed=holyimage.embed)

    @holyimage.autocomplete("game")
    async def holy_game_autocomplete(self, interaction: discord.Interaction, current: str):
        data = await get_holy_images()
        keys = sorted([val for val in data.keys() if val.startswith(current)][:25])
        return [app_commands.Choice(name=key, value=key) for key in keys]

    @holyimage.autocomplete("slug")
    async def holy_slug_autocomplete(self, interaction: discord.Interaction, current: str):
        data = await get_holy_images()
        value: str = current

        game = interaction.namespace.game
        if not game:
            if interaction.guild:
                game = await holy_game_default(interaction.guild)
            else:
                game = 'z3r'

        slugs = sorted([val['slug'] for val in data[game] if val['slug'].startswith(value)][:25])

        return [app_commands.Choice(name=slug, value=slug) for slug in slugs]

    @app_commands.command(name="datetime", description="Get discord markdown for the date specified.")
    @app_commands.describe(
        year="The year to use. Defaults to the current year.",
        month="The month to use. Defaults to the current month.",
        day="The day to use. Defaults to the current day.",
        hour="The hour to use. Defaults to 0.",
        minute="The minute to use. Defaults to 0.",
        second="The second to use. Defaults to 0.",
        timezone="Timezone to get the date for. Defaults to US/Eastern"
    )
    async def datetime_cmd(
        self,
        interaction: discord.Interaction,
        year: app_commands.Range[int, 1970, 9999] = None,
        month: app_commands.Range[int, 1, 12] = None,
        day: app_commands.Range[int, 1, 31] = None,
        hour: app_commands.Range[int, 0, 23] = 0,
        minute: app_commands.Range[int, 0, 59] = 0,
        second: app_commands.Range[int, 0, 59] = 0,
        timezone: str  = "US/Eastern"
    ):
        if year is None:
            year = datetime.datetime.now().year
        if month is None:
            month = datetime.datetime.now().month
        if day is None:
            day = datetime.datetime.now().day
        try:
            tz = pytz.timezone(timezone)
            time = tz.localize(datetime.datetime(year, month, day, hour, minute, second))
        except UnknownTimeZoneError:
            await interaction.response.send_message(f"Unknown timezone: {timezone}", ephemeral=True)
            return
        except ValueError:
            await interaction.response.send_message(f"Invalid date: {year}-{month}-{day} {hour}:{minute}:{second} {timezone}", ephemeral=True)
            return

        markdown = "Discord formatted datetime\n\n"

        for fmt in ["t", "T", "d", "D", "f", "F", "R"]:
            formatted_time = discord.utils.format_dt(time, fmt)
            markdown += f"{formatted_time} - `{formatted_time}`\n"

        embed = discord.Embed(
            title=f"Date markdown for {time.strftime('%Y-%m-%d %H:%M:%S')} {timezone}",
            description=markdown,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @datetime_cmd.autocomplete("timezone")
    async def datetime_autocomplete_tz(self, interaction: discord.Interaction, current: str):
        timezones = sorted([val for val in pytz.all_timezones if val.startswith(current)][:25])
        return [app_commands.Choice(name=timezone, value=timezone) for timezone in timezones]

async def setup(bot: commands.Command):
    await bot.add_cog(Misc(bot))
