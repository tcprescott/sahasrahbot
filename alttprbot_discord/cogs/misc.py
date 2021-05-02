import asyncio
import random

import discord
from discord.ext import commands

from alttprbot.database import config
from alttprbot.util.holyimage import HolyImage

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
                    await message.reply(f'@{message.author.mention}')

    @commands.group()
    async def welcome(self, ctx):
        pass

    @welcome.command(aliases=['fr'])
    async def french(self, ctx):
        await ctx.send(
            (
                'Bienvenue! Ce serveur discord est principalement en anglais.\n'
                'Vous trouverez un serveur en français en suivant https://discord.gg/9cWhQyw .\n'
                'Les membres de ce serveur se feront un plaisir de vous aider.\n\n'
                'Merci, et bienvenue encore une fois.'
            )
        )

    @welcome.command(aliases=['es'])
    async def spanish(self, ctx):
        await ctx.send(
            (
                '¡Bienvenidos! Este servidor de Discord es principalmente de habla inglesa.'
                '¡No tengáis miedo, hay un servidor en Español que podéis encontrar en https://discord.gg/xyHxAFJ donde os pueden ayudar!\n\n'
                'Gracias y otra vez, bienvenidos.'
            )
        )

    @welcome.command(aliases=['de'])
    async def german(self, ctx):
        await ctx.send(
            (
                'Willkommen! Auf diesem Server wird grundsätzlich in Englisch geschrieben.'
                'Aber keine Sorge, es gibt ebenfalls einen deutschen Discord-Server, der dir gerne in deiner Sprache helfen kann.'
                'Diesen findest du unter folgender Einladung https://discordapp.com/invite/5zuANcS . Dort gibt es alles - von Einsteigertipps bis zu Turnieren\n\n'
                'Vielen Dank und nochmals herzlich willkommen.'
            )
        )

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
        await ctx.reply(embed=embed)

    @commands.command()
    async def prng(self, ctx):
        await ctx.reply("PRNG is RNG!  It is random!  Humans tend to identify patterns where they do not exist.\n\nIf you're a Linux nerd check this out: https://www.2uo.de/myths-about-urandom/")

    @commands.command(hidden=True)
    async def pedestalgoal(self, ctx):
        await ctx.reply("> If it takes 2 hours its because GT is required, which really isn't a thing anymore in pedestal goal games\n-Synack")

    @commands.command(
        aliases=['crc32'],
        brief="Posts instructions on how to verify your ROM is correct.",
        help="Posts instructions on how to verify your ROM is correct, or how to get the permalink to your randomized game."
    )
    async def rom(self, ctx):
        await ctx.reply(
            "If you need help verifying your legally-dumped Japanese version 1.0 A Link to the Past Game file needed to run ALttPR, use this tool: <http://alttp.mymm1.com/game/checkcrc/>\n"
            "It can also help get the permalink page URL which has access to the Spoiler Log depending on the settings that were chosen. Not all games that are generated have access to the Spoiler Log.\n\n"
            "For legal reasons, we cannot provide help with finding this ROM online.  Please do not ask here for assistance with this.\n"
            "See <#543572578787393556> for details."
        )

    @commands.command(hidden=True)
    async def trpegs(self, ctx):
        await ctx.reply(discord.utils.get(ctx.bot.emojis, name='RIPLink'))

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
        await ctx.reply(msg)

    @commands.command(
        brief="Retrieves a holy image.",
        help="Retrieves a holy image from http://alttp.mymm1.com/holyimage/",
        aliases=['holy']
    )
    async def holyimage(self, ctx, slug, game=None):
        if game is None:
            if ctx.guild is None:
                game = "z3r"
            else:
                game = await config.get(ctx.guild.id, "HolyImageDefaultGame", "z3r")

        holyimage = await HolyImage.construct(slug=slug, game=game)

        await ctx.reply(embed=holyimage.embed)


def setup(bot):
    bot.add_cog(Misc(bot))
