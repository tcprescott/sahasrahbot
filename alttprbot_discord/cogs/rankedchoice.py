import discord
from discord import app_commands
from discord.ext import commands

import config
from alttprbot.exceptions import InvalidInputError, PermissionDeniedError
from alttprbot.services import ranked_choice
from alttprbot.util import rankedchoice

APP_URL = config.APP_URL


class RankedChoiceMessageView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="End Election", custom_id="sahasrahbot:rankedchoice:end_election",
                       style=discord.ButtonStyle.danger)
    async def end_election(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await interaction.response.send_message("Ending the election is not yet implemented.", ephemeral=True)
        await interaction.response.defer()
        try:
            election = await ranked_choice.end_election(interaction.message.id, interaction.user.id)
        except (PermissionDeniedError, InvalidInputError) as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        await rankedchoice.refresh_election_post(election, self.bot)

        await interaction.followup.send("Successfully ended the election.", ephemeral=True)


class RankedChoice(commands.GroupCog, name="rankedchoice"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(RankedChoiceMessageView(self.bot))
            self.persistent_views_added = True

    @app_commands.command(description="Create a ranked choice election.")
    @app_commands.describe(title="The title of the election.")
    @app_commands.describe(description="The description of the election.")
    @app_commands.describe(candidates="The candidates for the election, separated by commas.")
    @app_commands.describe(seats="The number of seats to fill in the election.")
    @app_commands.describe(
        authorized_voters_role="The role that is authorized to vote in the election.  If not specified, anyone can vote.")
    @app_commands.describe(show_vote_count="Whether or not to show who has voted in this election.")
    async def create(self, interaction: discord.Interaction, title: str, candidates: str, seats: int = 1,
                     description: str = None, authorized_voters_role: discord.Role = None,
                     show_vote_count: bool = True):

        if not interaction.user.guild_permissions.administrator and not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        election = await ranked_choice.create_election(
            title=title,
            description=description,
            candidates=candidates.split(','),
            seats=seats,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            owner_id=interaction.user.id,
            voter_role_id=authorized_voters_role.id if authorized_voters_role else None,
            show_vote_count=show_vote_count,
        )

        await interaction.response.send_message(embed=rankedchoice.create_embed(election),
                                                view=RankedChoiceMessageView(self.bot))
        message = await interaction.original_response()
        await ranked_choice.set_message_id(election.id, message.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(RankedChoice(bot))
