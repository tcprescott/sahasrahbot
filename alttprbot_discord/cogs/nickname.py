import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.util import discord_members


class RtggAdmin(commands.GroupCog, name="rtggadmin", description="Admin commands for rt.gg integration"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description="Used by Synack to blast requests to link your RaceTime.gg account to this bot.")
    @app_commands.describe(
        role="Choose a role to blast",
    )
    async def blast(self, interaction: discord.Interaction, role: discord.Role):
        # This walked every member of the role, which needs the privileged members intent.
        await interaction.response.send_message(discord_members.ROLE_MEMBERS_UNAVAILABLE, ephemeral=True)

    @app_commands.command(
        description="Used by Synack to report users who have not linked their racetime account to SahasrahBot.")
    @app_commands.describe(
        role="Choose a role to blast",
    )
    async def report(self, interaction: discord.Interaction, role: discord.Role):
        # This walked every member of the role, which needs the privileged members intent.
        await interaction.response.send_message(discord_members.ROLE_MEMBERS_UNAVAILABLE, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RtggAdmin(bot))
