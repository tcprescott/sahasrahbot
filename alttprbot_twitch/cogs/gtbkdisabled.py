from twitchio.ext import commands


@commands.core.cog()
class Gtbk():
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start(self, ctx):
        await ctx.send("GTBK game is currently disabled until further notice.  Sorry!")

    @commands.command()
    async def stop(self, ctx):
        await ctx.send("GTBK game is currently disabled until further notice.  Sorry!")

    @commands.command(aliases=['key'])
    async def bigkey(self, ctx):
        await ctx.send("GTBK game is currently disabled until further notice.  Sorry!")

    @commands.command()
    async def status(self, ctx):
        await ctx.send("GTBK game is currently disabled until further notice.  Sorry!")

    @commands.command()
    async def leaderboard(self, ctx):
        await ctx.send("GTBK game is currently disabled until further notice.  Sorry!")

    @commands.command()
    async def whitelist(self, ctx, twitch_user):
        await ctx.send("GTBK game is currently disabled until further notice.  Sorry!")


def setup(bot):
    bot.add_cog(Gtbk(bot))
