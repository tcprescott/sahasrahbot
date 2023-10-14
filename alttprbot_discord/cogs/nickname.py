import os
import logging

import discord
from discord import app_commands
from discord.ext import commands

from alttprbot import models

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')


class RtggAdmin(commands.GroupCog, name="rtggadmin", description="Admin commands for rt.gg integration"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description="Used by Synack to blast requests to link your RaceTime.gg account to this bot.")
    @app_commands.describe(
        role="Choose a role to blast",
    )
    async def blast(self, interaction: discord.Interaction, role: discord.Role):
        if not await self.bot.is_owner(interaction.user) and interaction.user.guild_permissions.administrator is False:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        msg = []
        if interaction.guild.chunked is False:
            await interaction.guild.chunk(cache=True)

        for member in role.members:
            result = await models.Users.get_or_none(discord_user_id=member.id)
            if result is None or result.rtgg_id is None:
                try:
                    await member.send(
                        (f"Greetings {member.name}!  We have detected that you do not have a RaceTime.gg ID linked to SahasrahBot.\n"
                         f"Please visit <{APP_URL}/racetime/verification/initiate> to verify your RaceTime.gg ID!  We will need this info.\n\n"
                         "If you have any questions, please contact Synack.  Thank you!")
                    )
                    msg.append(f"Send DM to {member.name}#{member.discriminator}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    msg.append(f"Failed to send DM to {member.name}#{member.discriminator}.\n\n{str(e)}")
                    logging.exception(f"Failed to send DM to {member.name}#{member.discriminator}.")

        if msg:
            await interaction.followup.send("\n".join(msg), ephemeral=True)
        else:
            await interaction.followup.send("No messages sent.", ephemeral=True)

    @app_commands.command(description="Used by Synack to report users who have not linked their racetime account to SahasrahBot.")
    @app_commands.describe(
        role="Choose a role to blast",
    )
    async def report(self, interaction: discord.Interaction, role: discord.Role):
        if not await self.bot.is_owner(interaction.user) and interaction.user.guild_permissions.administrator is False:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        msg = []
        if interaction.guild.chunked is False:
            await interaction.guild.chunk(cache=True)

        for member in role.members:
            result = await models.Users.get_or_none(discord_user_id=member.id)
            if result is None or result.rtgg_id is None:
                msg.append(f"{member.name}#{member.discriminator}")

        if msg:
            await interaction.followup.send("\n".join(msg), ephemeral=True)

        else:
            await interaction.followup.send("Everyone in this role is registered with the bot.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(RtggAdmin(bot))
