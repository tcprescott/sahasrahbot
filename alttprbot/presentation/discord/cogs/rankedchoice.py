import discord
from discord import app_commands
from discord.ext import commands

import config
from alttprbot import models
from alttprbot.util import rankedchoice

APP_URL = config.APP_URL


class RankedChoiceMessageView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    # @discord.ui.button(label="Vote", custom_id="vote", style=discord.ButtonStyle.primary)
    # async def vote(self, button: discord.ui.Button, interaction: discord.Interaction):
    #     await interaction.response.send_message(f"Vote at https://sahasrahbotapi.synack.live/ranked_choice/{self.election.id}", ephemeral=True)

    @discord.ui.button(label="End Election", custom_id="sahasrahbot:rankedchoice:end_election",
                       style=discord.ButtonStyle.danger)
    async def end_election(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await interaction.response.send_message("Ending the election is not yet implemented.", ephemeral=True)
        await interaction.response.defer()
        election = await models.RankedChoiceElection.get(message_id=interaction.message.id)

        if election.owner_id != interaction.user.id:
            await interaction.followup.send("You are not the owner of this election.", ephemeral=True)
            return

        if election.active is False:
            await interaction.followup.send("This election is already closed.", ephemeral=True)
            return

        await election.fetch_related('candidates')
        # await election.fetch_related('authorized_voters')
        await election.fetch_related('votes')

        await rankedchoice.calculate_results(election)

        election.active = False
        await election.save()

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

        if interaction.user.guild_permissions.administrator is False and self.bot.is_owner(interaction.user) is False:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        election = await models.RankedChoiceElection.create(
            title=title,
            description=description,
            private=authorized_voters_role is not None,
            active=True,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=None,  # set this later
            owner_id=interaction.user.id,
            show_vote_count=show_vote_count,
            seats=seats,
            voter_role_id=authorized_voters_role.id if authorized_voters_role else None
        )

        if interaction.guild.chunked is False:
            await interaction.guild.chunk(cache=True)

        await models.RankedChoiceCandidate.bulk_create(
            [models.RankedChoiceCandidate(election=election, name=candidate.strip()) for candidate in
             candidates.split(',')])
        # if authorized_voters_role:
        #     await models.RankedChoiceAuthorizedVoters.bulk_create([models.RankedChoiceAuthorizedVoters(election=election, user_id=user_id) for user_id in [member.id for member in authorized_voters_role.members]])

        await election.fetch_related('candidates')
        # await election.fetch_related('authorized_voters')
        await election.fetch_related('votes')

        await interaction.response.send_message(embed=rankedchoice.create_embed(election),
                                                view=RankedChoiceMessageView(self.bot))
        message = await interaction.original_response()
        election.message_id = message.id
        await election.save()

    # @app_commands.command(description="Refresh the .")
    # @app_commands.describe(election_id="The ID of the election.")
    # async def status(self, interaction: discord.Interaction, election_id: int):
    #     election = await models.RankedChoiceElection.get(id=election_id)
    #     await election.fetch_related('candidates')
    #     await election.fetch_related('authorized_voters')
    #     await election.fetch_related('votes')

    #     await interaction.response.send_message(embed=rankedchoice.create_embed(election))

    # @app_commands.command(description="Forcibly refresh the election post.")
    # @app_commands.describe(election_id="The ID of the election.")
    # async def refresh(self, interaction: discord.Interaction, election_id: int):
    #     election = await models.RankedChoiceElection.get(id=election_id)
    #     await election.fetch_related('candidates')
    #     await election.fetch_related('authorized_voters')
    #     await election.fetch_related('votes')

    #     await rankedchoice.refresh_election_post(election, self.bot)
    #     await interaction.response.send_message(f"Refreshed election post.", ephemeral=True)

    # @app_commands.command(description="Temp command")
    # @app_commands.describe(election_id="The ID of the election.")
    # async def temp(self, interaction: discord.Interaction, election_id: int):
    #     await interaction.response.defer()
    #     election = await models.RankedChoiceElection.get(id=election_id)
    #     await election.fetch_related('candidates')
    #     await election.fetch_related('authorized_voters')
    #     await election.fetch_related('votes')

    #     await rankedchoice.calculate_results(election)

    #     election.active = False
    #     await election.save()

    #     await rankedchoice.refresh_election_post(election, self.bot)
    #     await interaction.followup.send("Successfully ended the election.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RankedChoice(bot))
