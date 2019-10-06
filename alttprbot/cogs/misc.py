import json
from urllib.parse import urljoin

import aiocache
import aiohttp
import discord
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='joineddate')
    @commands.is_owner()
    async def group_list(self, ctx, member: discord.Member):
        await ctx.send(member.joined_at)

    @commands.command(hidden=True)
    async def pedestalgoal(self, ctx):
        await ctx.send("> If it takes 2 hours its because GT is required, which really isn't a thing anymore in pedestal goal games\n-Synack")

    @commands.command(aliases=['rom'])
    async def crc32(self, ctx):
        await ctx.send("If you need help verifying your legally dumped Japan 1.0 rom file needed for ALTTPR, check this out: http://alttp.mymm1.com/game/checkcrc/\nIt can also tell you the permalink of an already randomized game!\n\nFor legal reasons, we cannot provide help with finding this ROM online.")

    @commands.command()
    async def holyimage(self, ctx, slug, game='z3r'):
        images = await get_json('http://alttp.mymm1.com/holyimage/holyimages.json')
        i = images[game]
        image = next(item for item in i if item["slug"] == slug)
        url = urljoin('http://alttp.mymm1.com/holyimage/',image['url'])
        link = f"http://alttp.mymm1.com/holyimage/{game}-{slug}.html"
        await ctx.send(
            f"{image['title']}\n\n{url}\n\nLink: <{link}>"
        )


@aiocache.cached(ttl=3600, cache=aiocache.SimpleMemoryCache)
async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)

def setup(bot):
    bot.add_cog(Misc(bot))
