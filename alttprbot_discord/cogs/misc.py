import asyncio
import json
import random
from urllib.parse import urljoin

import aiocache
import aiohttp
import discord
import html2markdown
from discord.ext import commands

from alttprbot.util.holyimage import holy


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content.lower() == '!role furaime':
            await message.add_reaction('👀')
        if discord.utils.get(message.role_mentions, id=524738280630124574):
            if random.choice([True, False]):
                await asyncio.sleep((random.random()*30)+30)
                await message.channel.send(f'@{message.author.mention}')

    @commands.command(aliases=['joineddate'])
    @commands.check_any(
        commands.has_any_role(523276397679083520, 307883683526868992),
        commands.has_permissions(administrator=True),
        commands.has_permissions(manage_guild=True)
    )
    async def memberinfo(self, ctx, member: discord.Member=None):
        if member is None:
            member = ctx.author
        embed = discord.Embed(
            title=f"Member info for {member.name}#{member.discriminator}",
            color=member.color
        )
        embed.add_field(name='Created at', value=member.created_at, inline=False)
        embed.add_field(name='Joined at', value=member.joined_at, inline=False)
        embed.add_field(name="Discord ID", value=member.id, inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def throwerror(self, ctx):
        raise Exception('omg')

    @commands.command()
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
