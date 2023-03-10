import discord
from discord.ext import commands
from discord import app_commands

from alttprbot import models

class Admin(commands.GroupCog, name="admin"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description="Used by Synack to update display names in the bot.")
    async def fixnames(self, interaction: discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        users = await models.Users.filter(discord_user_id__isnull=False, display_name__isnull=True)

        updated = 0

        for user in users:
            member = await self.bot.fetch_user(user.discord_user_id)
            if member is not None:
                user.name = member.display_name
                await user.save()
                updated += 1

        await interaction.followup.send(f"Done. Performed {updated} changes.", ephemeral=True)

async def setup(bot: commands.Bot):
    bot.add_cog(Admin(bot))
