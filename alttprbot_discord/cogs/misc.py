import json
from urllib.parse import urljoin

import aiocache
import aiohttp
import discord
import html2markdown
from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.util.holyimage import holy


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def joineddate(self, ctx, member: discord.Member):
        await ctx.send(member.joined_at)

    @commands.command()
    @commands.is_owner()
    async def throwerror(self, ctx):
        raise Exception('omg')

    @commands.command(hidden=True)
    async def pedestalgoal(self, ctx):
        await ctx.send("> If it takes 2 hours its because GT is required, which really isn't a thing anymore in pedestal goal games\n-Synack")

    @commands.command(
        aliases=['crc32'],
        brief="Posts instructions on how to verify your ROM is correct.",
        help="Posts instructions on how to verify your ROM is correct, or how to get the permalink to your randomized game."
    )
    async def rom(self, ctx):
        await ctx.send("If you need help verifying your legally dumped Japan 1.0 rom file needed for ALTTPR, check this out: http://alttp.mymm1.com/game/checkcrc/\nIt can also tell you the permalink of an already randomized game!\n\nFor legal reasons, we cannot provide help with finding this ROM online.")

    @commands.command(hidden=True)
    async def trpegs(self, ctx):
        await ctx.send(discord.utils.get(ctx.bot.emojis, name='RIPLink'))

    @commands.command(
        brief="Retrieves a holy image.",
        help="Retrieves a holy image from http://alttp.mymm1.com/holyimage/",
        aliases=['holy']
    )
    async def holyimage(self, ctx, slug=None, game='z3r'):
        holyimage = await holy(slug=slug, game=game)

        embed = discord.Embed(
            title=holyimage.image.get('title'),
            description=html2markdown.convert(holyimage.image['desc']) if 'desc' in holyimage.image else None,
            color=discord.Colour.from_rgb(0xFF, 0xAF, 0x00)
        )

        if 'url' in holyimage.image:
            url = urljoin('http://alttp.mymm1.com/holyimage/', holyimage.image['url'])
            if holyimage.image.get('mode', '') == 'redirect':
                embed.add_field(name='Link', value=url, inline=False)
            else:
                embed.set_thumbnail(url=url)

        embed.add_field(name="Source", value=holyimage.link)

        if 'credit' in holyimage.image:
            embed.set_footer(text=f"Created by {holyimage.image['credit']}")

        await ctx.send(embed=embed)


@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(Misc(bot))
