import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option


class Test(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # self.bot.add_application_command(self.test_grp)

    # test_grp = SlashCommandGroup(name="test", description="This is a test command")

    # @test_grp.command(name="testcmd")
    # async def testcmd(self, ctx, testarg: Option(str, description="test arg")):
    #     await ctx.respond(testarg)


def setup(bot):
    bot.add_cog(Test(bot))
