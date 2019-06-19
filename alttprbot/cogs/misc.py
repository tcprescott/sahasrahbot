
import discord
from discord.ext import commands

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='joineddate')
    @commands.is_owner()
    async def group_list(self, ctx, member: discord.Member):
        await ctx.send(member.joined_at)

def setup(bot):
    bot.add_cog(Misc(bot))