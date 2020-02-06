import discord
from discord.ext import commands

class RaceBot(commands.Cog):
    @commands.command(aliases=['enter'])
    async def join(self, ctx):
        pass

    @commands.command(aliases=['leave', 'forfeit'])
    async def quit(self, ctx):
        pass

    @commands.command()
    async def ready(self, ctx):
        pass

    @commands.command()
    async def done(self, ctx):
        pass

    @commands.command()
    async def undone(self, ctx):
        pass

    @commands.command()
    async def time(self, ctx):
        pass

    @commands.command()
    async def entrants(self, ctx):
        pass

    @commands.command()
    async def game(self, ctx, game=None):
        pass

    @commands.command()
    async def goal(self, ctx, goal=None):
        pass

    @commands.command()
    async def racenote(self, ctx, note):
        pass

    @commands.group()
    async def racemod(self, ctx):
        pass

    @racemod.command()
    async def disqualify(self, ctx, player: discord.Member):
        pass

    @racemod.command()
    async def end(self, ctx):
        pass

    @racemod.command()
    async def remove(self, ctx, player: discord.Member):
        pass

def setup(bot):
    bot.add_cog(RaceBot(bot))
