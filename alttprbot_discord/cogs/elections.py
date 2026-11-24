"""Elections are created and managed on the website (``/elections``). This cog keeps
the End election button on election posts working across restarts, and gives admins
``/rankedchoice create``, which links to the website's form."""

from urllib.parse import urlencode

import discord
from discord import app_commands
from discord.ext import commands

import config
from alttprbot_discord.elections import ElectionView


def create_url(guild_id: int, channel_id: int) -> str:
    """The new-election form, starting on this server and channel. Ids stay strings in
    the URL; the web app checks them against the servers you administer."""
    return f"{config.APP_URL}/elections/new?{urlencode({'server': guild_id, 'channel': channel_id})}"


class Elections(commands.Cog):
    rankedchoice = app_commands.Group(
        name="rankedchoice",
        description="Elections, run on the SahasrahBot website.",
        guild_only=True,
        # Hidden from everyone without Administrator; server owners can change that in Integrations.
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(ElectionView())
            self.persistent_views_added = True

    @rankedchoice.command(name="create", description="Create an election on the website, for this server and channel.")
    async def create(self, interaction: discord.Interaction):
        channel = interaction.channel
        # In a thread, the election goes in the thread's channel.
        channel_id = getattr(channel, "parent_id", None) or channel.id
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Create election", url=create_url(interaction.guild.id, channel_id)))
        view.add_item(discord.ui.Button(label="All elections", url=f"{config.APP_URL}/elections"))
        await interaction.response.send_message(
            f"Create the election on the website. The form opens with this server and <#{channel_id}> already picked.",
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Elections(bot))
