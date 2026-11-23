from discord.ext import commands


class Test(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Test(bot))
