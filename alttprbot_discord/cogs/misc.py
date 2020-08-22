import asyncio
import datetime
import random
from urllib.parse import urljoin

import dateutil.parser
import discord
import html2markdown
import pytz
from discord.ext import commands

from alttprbot.util import speedgaming
from alttprbot.util.holyimage import holy

from ..util import checks


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.lower() == '!role furaime':
            await message.add_reaction('👀')

        if self.bot.user in message.mentions:
            emoji = discord.utils.get(self.bot.emojis, name='SahasrahBot')
            if emoji:
                await asyncio.sleep(random.random()*5)
                await message.add_reaction(emoji)

        if discord.utils.get(message.role_mentions, id=524738280630124574):
            async with message.channel.typing():
                await asyncio.sleep((random.random()*30)+30)
                if random.choice([True, False]):
                    await message.channel.send(f'@{message.author.mention}')

    @commands.command(aliases=['joineddate'])
    @commands.check_any(
        commands.has_any_role(523276397679083520, 307883683526868992),
        commands.has_permissions(administrator=True),
        commands.has_permissions(manage_guild=True),
        checks.has_any_channel_id(608008164356653066)
    )
    async def memberinfo(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        embed = discord.Embed(
            title=f"Member info for {member.name}#{member.discriminator}",
            color=member.color
        )
        embed.add_field(name='Created at',
                        value=member.created_at, inline=False)
        embed.add_field(name='Joined at', value=member.joined_at, inline=False)
        embed.add_field(name="Discord ID", value=member.id, inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=embed)

<<<<<<< HEAD
    @commands.command()
=======
    @commands.command(hidden=True)
    @commands.is_owner()
    async def throwerror(self, ctx):
        raise Exception('omg')

    @commands.command(hidden=True)
>>>>>>> sql_overhaul
    async def prng(self, ctx):
        await ctx.send("PRNG is RNG!  It is random!  Humans tend to identify patterns where they do not exist.\n\nIf you're a Linux nerd check this out: https://www.2uo.de/myths-about-urandom/")

    @commands.command(hidden=True)
    async def pedestalgoal(self, ctx):
        await ctx.send("> If it takes 2 hours its because GT is required, which really isn't a thing anymore in pedestal goal games\n-Synack")

    @commands.command(
        aliases=['crc32'],
        brief="Posts instructions on how to verify your ROM is correct.",
        help="Posts instructions on how to verify your ROM is correct, or how to get the permalink to your randomized game."
    )
    async def rom(self, ctx):
        await ctx.send(
            "If you need help verifying your legally-dumped Japanese version 1.0 A Link to the Past Game file needed to run ALttPR, use this tool: <http://alttp.mymm1.com/game/checkcrc/>\n"
            "It can also help get the permalink page URL which has access to the Spoiler Log depending on the settings that were chosen. Not all games that are generated have access to the Spoiler Log.\n\n"
            "For legal reasons, we cannot provide help with finding this ROM online.  Please do not ask here for assistance with this.\n"
            "See <#543572578787393556> for details."
        )

    @commands.command(hidden=True)
    async def trpegs(self, ctx):
        await ctx.send(discord.utils.get(ctx.bot.emojis, name='RIPLink'))

    @commands.command(hidden=True, aliases=['8ball'])
    async def eightball(self, ctx):
      msg = random.choice([
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes – definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful.",
      ])
      await ctx.send(msg)


    @commands.command(
        brief="Retrieves a holy image.",
        help="Retrieves a holy image from http://alttp.mymm1.com/holyimage/",
        aliases=['holy']
    )
    async def holyimage(self, ctx, slug=None, game='z3r'):
        holyimage = await holy(slug=slug, game=game)

        embed = discord.Embed(
            title=holyimage.image.get('title'),
            description=html2markdown.convert(
                holyimage.image['desc']) if 'desc' in holyimage.image else None,
            color=discord.Colour.from_rgb(0xFF, 0xAF, 0x00)
        )

        if 'url' in holyimage.image:
            url = urljoin('http://alttp.mymm1.com/holyimage/',
                          holyimage.image['url'])
            if holyimage.image.get('mode', '') == 'redirect':
                embed.add_field(name='Link', value=url, inline=False)
            else:
                embed.set_thumbnail(url=url)

        embed.add_field(name="Source", value=holyimage.link)

        if 'credit' in holyimage.image:
            embed.set_footer(text=f"Created by {holyimage.image['credit']}")

        await ctx.send(embed=embed)

    @commands.command(
        brief="Retrieves the next ALTTPR SG daily race.",
        help="Retrieves the next ALTTPR SG daily race.",
    )
    @commands.cooldown(rate=1, per=900, type=commands.BucketType.channel)
    async def sgdaily(self, ctx, get_next=1):
        sg_schedule = await speedgaming.get_upcoming_episodes_by_event('alttprdaily', hours_past=0, hours_future=192)
        if len(sg_schedule) == 0:
            await ctx.send("There are no currently SpeedGaming ALTTPR Daily Races scheduled within the next 8 days.")
            return
        
        if get_next == 1:
            embed = discord.Embed(
                title=sg_schedule[0]['event']['name'],
                description=f"**Mode:** {'*TBD*' if sg_schedule[0]['match1']['title'] == '' else sg_schedule[0]['match1']['title']}\n[Full Schedule](http://speedgaming.org/alttprdaily)"
            )
        else:
            embed = discord.Embed(
                title="ALTTP Randomizer SG Daily Schedule",
                description="[Full Schedule](http://speedgaming.org/alttprdaily)"
            )

        for episode in sg_schedule[0:get_next]:
            when = dateutil.parser.parse(episode['when'])
            when_central = when.astimezone(pytz.timezone(
                'US/Eastern')).strftime('%m-%d %I:%M %p')
            when_europe = when.astimezone(pytz.timezone(
                'Europe/Berlin')).strftime('%m-%d %I:%M %p')
            difference = when - datetime.datetime.now(when.tzinfo)

            if get_next == 1:
                embed.add_field(
                    name='Time', value=f"**US:** {when_central} Eastern\n**EU:** {when_europe} CET/CEST\n\n{round(difference / datetime.timedelta(hours=1), 1)} hours from now", inline=False)
                broadcast_channels = [a['name']
                                    for a in episode['channels'] if not a['name'] == 'No Stream']
                if broadcast_channels:
                    embed.add_field(name="Twitch Channels", value=', '.join(
                        [f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
            else:
                embed.add_field(
                    name='TBD' if episode['match1']['title'] == '' else episode['match1']['title'],
                    value=(
                        f"**US:** {when_central} Eastern\n"
                        f"**EU:** {when_europe} CET/CEST\n\n"
                    ),
                    inline=False
                )
        embed.set_footer()

        embed.set_thumbnail(
            url='https://pbs.twimg.com/profile_images/1185422684190105600/3jiXIf5Y_400x400.jpg')
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Misc(bot))
