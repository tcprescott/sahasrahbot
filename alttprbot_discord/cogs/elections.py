"""Elections are created and managed on the website (``/elections``). This cog only
keeps the End election button on election posts working across restarts."""

from discord.ext import commands

from alttprbot_discord.elections import ElectionView


class Elections(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(ElectionView())
            self.persistent_views_added = True


async def setup(bot: commands.Bot):
    await bot.add_cog(Elections(bot))
