from discord.ext import commands

from alttprbot_discord.util.config import GuildConfig


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if await ctx.bot.is_owner(ctx.author):
            return True

        return False

    @commands.group()
    async def config(self, ctx):
        pass

    @config.command()
    async def set(self, ctx, parameter, value):
        ctx.guild.config.set(parameter, value)

    @config.command()
    async def get(self, ctx):
        await ctx.reply(ctx.guild.config.dump())

    @config.command()
    async def delete(self, ctx, parameter):
        ctx.guild.config.delete(parameter)

    @config.command()
    async def reloadall(self, ctx):
        for guild in self.bot.guilds():
            guild.config = GuildConfig(guild.id)


def setup(bot):
    bot.add_cog(Config(bot))
