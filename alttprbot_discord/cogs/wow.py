import discord
from discord.ext import commands
from discord.commands import Option

class GamblingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, error: Exception, item, interaction) -> None:
        raise error

    @discord.ui.button(label="Join", style=discord.ButtonStyle.blurple, custom_id="sahabot:wowgamble:join", row=1)
    async def join(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, custom_id="sahabot:wowgamble:leave", row=1)
    async def leave(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, custom_id="sahabot:wowgamble:start", row=2)
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="sahabot:wowgamble:cancel", row=2)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass


class WorldOfWarcraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.persistent_views_added = False

    @ commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(GamblingView())
            self.persistent_views_added = True

    @commands.slash_command(name='gamble')
    async def gamble(
        self,
        ctx: discord.ApplicationContext,
        stake: Option(int, description="Gold to stake on the game.", required=True),
        dryrun: Option(bool, description="Dry run mode.", default=False),
        timeout: Option(int, description="Seconds to wait for the game to start.") = 60,
    ):
        """
        Search for a WoW character.
        """
        embed = discord.Embed(title="Gamble", description="Gamble on the game.", color=discord.Color.gold())
        embed.add_field(name="Stake", value=f"{stake}g", inline=False)
        embed.add_field(name="Time left", value="1 minute", inline=False)
        embed.add_field(name="Entrants", value="No entrants.", inline=False)
        embed.add_field(name="Winner", value="No winner yet.", inline=False)
        msg = await ctx.send(embed=embed)
        await msg.create_thread(name=f"Gambling session by {ctx.author.name}")

async def setup(bot):
    await bot.add_cog(WorldOfWarcraft(bot))
