from discord.ext import commands

class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild is None:
            return False
        return False

    @commands.command(
        help='Set the ALTTPR League Week.'
    )
    @commands.has_any_role('Admin', 'Mods', 'Bot Overlord')
    async def setleagueweek(self, ctx, week):
        guildid = ctx.guild.id if ctx.guild else 0

    @commands.command(
        help='Get the league week.'
    )
    async def getleagueweek(self, ctx):
        guildid = ctx.guild.id if ctx.guild else 0

def setup(bot):
    bot.add_cog(League(bot))
