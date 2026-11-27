import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.services import discord_servers


class DiscordServers(commands.GroupCog, name="discordservers", description="Manage the server directory (also on the website, under Servers)."):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description="Add a category to the discord server list.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def add_category(self, interaction: discord.Interaction,
                           channel: discord.TextChannel,
                           category_title: str,
                           category_description: str = None,
                           order: int = 0
                           ):
        await discord_servers.add_category(interaction.guild.id, channel.id, category_title, category_description, order)
        await interaction.response.send_message(f"Added category {category_title} to {channel.mention}", ephemeral=True)

    @app_commands.command(description="List all categories for the discord server list.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def list_category(self, interaction: discord.Interaction):
        results = await discord_servers.list_categories(interaction.guild.id)
        if results:
            embed = discord.Embed(
                title="List of categories",
                color=discord.Colour.blue(),
            )
            for result in results:
                channel = interaction.guild.get_channel(result.channel_id)
                embed.add_field(
                    name=result.category_title,
                    value=f"_*Id:*_ {result.id}\n_*Channel:*_ {channel.mention}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No categories found.", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_category(self, interaction: discord.Interaction, category_id: int):
        await discord_servers.remove_category(interaction.guild.id, category_id)
        await interaction.response.send_message(f"Removed category {category_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def update_category(self, interaction: discord.Interaction, category_id: int, category_title: str,
                              category_description: str, order: int = 0):
        await discord_servers.update_category(interaction.guild.id, category_id, category_title, category_description, order)
        await interaction.response.send_message(f"Updated category {category_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def add_server(self, interaction: discord.Interaction, category_id: int, invite_url: str,
                         server_description: str):
        """
        Add a server to a category.
        """
        invite = await self.bot.fetch_invite(invite_url)
        await discord_servers.add_server(interaction.guild.id, category_id, invite.id, server_description)
        await interaction.response.send_message(f"Added server {invite.guild.name} to category {category_id}",
                                                ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def list_servers(self, interaction: discord.Interaction, category_id: int):
        """
        List all servers in a category.
        """
        results = await discord_servers.list_servers(interaction.guild.id, category_id)

        if results:
            embed = discord.Embed(
                title=f"Server list for category id {category_id}",
                color=discord.Colour.blue(),
            )
            for result in results:
                embed.add_field(
                    name=result.server_description,
                    value=f"_*Id:*_ {result.id}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"No servers found for category {category_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_server(self, interaction: discord.Interaction, server_id: int):
        """
        Remove a server from the discord server list.
        """
        await discord_servers.remove_server(interaction.guild.id, server_id)
        await interaction.response.send_message(f"Removed server {server_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def update_server(self, interaction: discord.Interaction, server_id: int, invite_url: str, category_id: int,
                            server_description: str = None):
        """
        Update a server in the discord server list.
        """
        invite = await self.bot.fetch_invite(invite_url)
        await discord_servers.update_server(interaction.guild.id, server_id, invite.id, category_id, server_description)
        await interaction.response.send_message(f"Updated server {server_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def refresh(self, interaction: discord.Interaction):
        """
        Refresh the discord server list.
        """
        await interaction.response.defer()
        await discord_servers.post(interaction.guild.id)
        await interaction.followup.send(f"Refreshed server list for {interaction.guild.name}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(DiscordServers(bot))
