import asyncio
import datetime
import random
import os
from aiocache import cached, Cache
import aiohttp

import discord
from discord.commands import Option
from discord.ext import commands
import pytz
from pytz import UnknownTimeZoneError

from alttprbot.util.holyimage import HolyImage


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


async def holy_slug_autocomplete(ctx):
    data = await get_holy_images()
    value: str = ctx.value

    raw_game = ctx.options['game']
    if raw_game:
        game = raw_game[0]['value']
    else:
        if ctx.interaction.guild:
            game = await holy_game_default(ctx.interaction.guild)
        else:
            game = 'z3r'

    slugs = sorted([val['slug'] for val in data[game] if val['slug'].startswith(value)][:25])

    return slugs


async def holy_game_autocomplete(ctx):
    data = await get_holy_images()
    return sorted([val for val in data.keys() if val.startswith(ctx.value)][:25])

async def datetime_autocomplete_tz(ctx):
    return sorted([val for val in pytz.all_timezones if val.startswith(ctx.value)][:25])

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

    @commands.slash_command(name="welcome", guild_ids=ALTTP_RANDOMIZER_SERVERS)
    async def welcome_cmd(self, ctx: discord.ApplicationContext, language: Option(str, description="Choose a language for the welcome message.", choices=WELCOME_MESSAGES.keys())):
        """
        Welcome messages for various languages.
        """
        await ctx.respond(WELCOME_MESSAGES[language])

    @commands.slash_command(name="memberinfo", guild_only=True)
    async def memberinfo_cmd(self, ctx, member: Option(discord.Member, "Choose a member")):
        """
        Get information about a member.
        """
        if member is None:
            member = ctx.author
        embed = discord.Embed(
            title=f"Member info for {member.name}#{member.discriminator}",
            color=member.color
        )
        embed.add_field(name='Created at', value=discord.utils.format_dt(member.created_at, style='F'), inline=False)
        embed.add_field(name='Joined at', value=discord.utils.format_dt(member.joined_at, style='F'), inline=False)
        embed.add_field(name="Discord ID", value=member.id, inline=False)
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="rom",
        guild_ids=ALTTP_RANDOMIZER_SERVERS
    )
    async def rom_cmd(self, ctx):
        """
        Get info about how to verify a ROM.
        """
        await ctx.respond(
            "If you need help verifying your legally-dumped Japanese version 1.0 A Link to the Past Game file needed to run ALTTPR, use this tool: <http://alttp.mymm1.com/game/checkcrc/>\n"
            "It can also help get the permalink page URL which has access to the Spoiler Log depending on the settings that were chosen. Not all games that are generated have access to the Spoiler Log.\n\n"
            "For legal reasons, we cannot provide help with finding this ROM online.  Please do not ask here for assistance with this.\n"
            "See <#543572578787393556> for details."
        )

    @commands.slash_command(guild_ids=ALTTP_RANDOMIZER_SERVERS)
    async def festive(self, ctx: discord.ApplicationContext):
        """
        Get info about festive randomizers.
        """
        embed = discord.Embed(
            title='Festive Randomizer Information',
            description='Latest details of any upcoming festive randomizers.',
            color=discord.Color.red()
        )
        embed.set_image(
            url='https://cdn.discordapp.com/attachments/307860211333595146/654123045375442954/unknown.png')

        await ctx.respond(embed=embed)

    @commands.slash_command(
        name='holyimage'
    )
    async def holyimage_cmd(
        self,
        ctx,
        slug: Option(str, description="Slug of the holy image to retrieve.", autocomplete=holy_slug_autocomplete),
        game: Option(str, description="Slug of the game to pull a holy image for.", required=False, autocomplete=holy_game_autocomplete)
    ):
        """
        Retrieves a holy image from http://alttp.mymm1.com/holyimage/
        """
        if game is None:
            if ctx.guild is None:
                game = "z3r"
            else:
                game = await ctx.guild.config_get("HolyImageDefaultGame", "z3r")

        holyimage = await HolyImage.construct(slug=slug, game=game)

        await ctx.respond(embed=holyimage.embed)

    @commands.slash_command(name="datetime")
    async def datetime_cmd(
        self,
        ctx: discord.ApplicationContext,
        year: Option(int, description="Year to get the date for.  Defaults to the current year.", required=False, min_value=1970, max_value=9999) = None,
        month: Option(int, description="Month to get the date for.  Defaults to the current month.", required=False, min_value=1, max_value=12) = None,
        day: Option(int, description="Day to get the date for.   Defaults to the current day.", required=False, min_value=1, max_value=31) = None,
        hour: Option(int, description="Hour to get the date for. (24 hour)", required=False, min_value=0, max_value=23) = 0,
        minute: Option(int, description="Minute to get the date for.", required=False, min_value=0, max_value=59) = 0,
        second: Option(int, description="Second to get the date for.", required=False, min_value=0, max_value=59) = 0,
        timezone: Option(str, description="Timezone to get the date for. Defaults to US/Eastern", required=False, autocomplete=datetime_autocomplete_tz) = "US/Eastern",
    ):
        """
        Get discord markdown for the date specified.
        """
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
            await ctx.respond(f"Unknown timezone: {timezone}", ephemeral=True)
            return
        except ValueError:
            await ctx.respond(f"Invalid date: {year}-{month}-{day} {hour}:{minute}:{second} {timezone}", ephemeral=True)
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
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(Misc(bot))
