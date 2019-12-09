import json
from urllib.parse import urljoin
from html.parser import HTMLParser
import datetime

import aiocache
import aiohttp
import discord
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def joineddate(self, ctx, member: discord.Member):
        await ctx.send(member.joined_at)

    @commands.command(hidden=True)
    async def pedestalgoal(self, ctx):
        await ctx.send("> If it takes 2 hours its because GT is required, which really isn't a thing anymore in pedestal goal games\n-Synack")

    @commands.command(
        aliases=['crc32'],
        help="Posts instructions on how to verify your ROM is correct, or how to get the permalink to your randomized game."
    )
    async def rom(self, ctx):
        await ctx.send("If you need help verifying your legally dumped Japan 1.0 rom file needed for ALTTPR, check this out: http://alttp.mymm1.com/game/checkcrc/\nIt can also tell you the permalink of an already randomized game!\n\nFor legal reasons, we cannot provide help with finding this ROM online.")

    @commands.command(
        help="Retrieves a holy image from http://alttp.mymm1.com/holyimage/",
        aliases=['holy']
    )
    async def holyimage(self, ctx, slug=None, game='z3r'):
        if slug is None: raise Exception('You must specify a holy image.  Check out <http://alttp.mymm1.com/holyimage/>')

        images = await get_json('http://alttp.mymm1.com/holyimage/holyimages.json')
        i = images[game]

        try:
            image = next(item for item in i if item["slug"] == slug or slug in item.get("aliases", []) or str(item["idx"]) == slug)
        except StopIteration:
            raise Exception('That holy image does not exist.  Check out <http://alttp.mymm1.com/holyimage/>')

        link = f"http://alttp.mymm1.com/holyimage/{game}-{image['slug']}.html"

        embed = discord.Embed(
            title=image.get('title'),
            description=None if not 'desc' in image else strip_tags(image['desc']),
            color=discord.Colour.dark_green()
        )

        if 'url' in image:
            url = urljoin('http://alttp.mymm1.com/holyimage/',image['url'])
            if image.get('mode','') == 'redirect':
                embed.add_field(name='Link', value=url, inline=False)
            else:
                embed.set_image(url=url)

        embed.add_field(name="Source", value=link)


        await ctx.send(embed=embed)


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache)
async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def setup(bot):
    bot.add_cog(Misc(bot))
