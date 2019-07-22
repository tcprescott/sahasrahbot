
import discord
from discord.ext import commands

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='joineddate')
    @commands.is_owner()
    async def group_list(self, ctx, member: discord.Member):
        await ctx.send(member.joined_at)

    @commands.command()
    async def crc32(self, ctx):
        await ctx.send("If you need help verifying your ROM file needed for ALTTPR, check this out: http://alttp.mymm1.com/game/checkcrc/\nIt can also tell you the permalink to an already randomized game too!")

def setup(bot):
    bot.add_cog(Misc(bot))