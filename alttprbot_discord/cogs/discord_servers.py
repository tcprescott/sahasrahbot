from importlib.metadata import requires
import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.database import discord_server_lists  # TODO switch to ORM

# TODO add autocomplete for arguments

class DiscordServers(commands.GroupCog, name="discordservers", description="Manage catagories."):
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
        await discord_server_lists.add_category(interaction.guild.id, channel.id, category_title=category_title, category_description=category_description, order=order)
        await interaction.response.send_message(f"Added category {category_title} to {channel.mention}", ephemeral=True)

    @app_commands.command(description="List all categories for the discord server list.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def list_category(self, interaction: discord.Interaction):
        results = await discord_server_lists.get_categories(interaction.guild.id)
        if results:
            embed = discord.Embed(
                title="List of categories",
                color=discord.Colour.blue(),
            )
            for result in results:
                channel = interaction.guild.get_channel(result['channel_id'])
                embed.add_field(
                    name=result['category_title'],
                    value=f"_*Id:*_ {result['id']}\n_*Channel:*_ {channel.mention}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No categories found.", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_category(self, interaction: discord.Interaction, category_id: int):
        await discord_server_lists.remove_category(interaction.guild.id, category_id)
        await interaction.response.send_message(f"Removed category {category_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def update_category(self, interaction: discord.Interaction, category_id: int, category_title: str, category_description: str, order: int = 0):
        await discord_server_lists.update_category(category_id, interaction.guild.id, category_title, category_description, order)
        await interaction.response.send_message(f"Updated category {category_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def add_server(self, interaction: discord.Interaction, category_id: int, invite_url: str, server_description: str):
        """
        Add a server to a category.
        """
        invite = await self.bot.fetch_invite(invite_url)
        await discord_server_lists.add_server(interaction.guild.id, invite.id, category_id, server_description=server_description)
        await interaction.response.send_message(f"Added server {invite.guild.name} to category {category_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def list_servers(self, interaction: discord.Interaction, category_id: int):
        """
        List all servers in a category.
        """
        results = await discord_server_lists.get_servers_for_category(category_id)

        if results:
            embed = discord.Embed(
                title=f"Server list for category id {category_id}",
                color=discord.Colour.blue(),
            )
            for result in results:
                embed.add_field(
                    name=result['server_description'],
                    value=f"_*Id:*_ {result['id']}",
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
        await discord_server_lists.remove_server(interaction.guild.id, server_id)
        await interaction.response.send_message(f"Removed server {server_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def update_server(self, interaction: discord.Interaction, server_id: int, invite_url: str, category_id: int, server_description: str = None):
        """
        Update a server in the discord server list.
        """
        invite = await self.bot.fetch_invite(invite_url)
        await discord_server_lists.update_server(interaction.guild.id, server_id, invite.id, category_id, server_description)
        await interaction.response.send_message(f"Updated server {server_id}", ephemeral=True)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def refresh(self, interaction: discord.Interaction):
        """
        Refresh the discord server list.
        """
        await interaction.response.defer()

        def is_me(m):
            return m.author == self.bot.user

        categories = await discord_server_lists.get_categories(interaction.guild.id)
        channels_to_update = list(set([c['channel_id'] for c in categories]))

        for c in channels_to_update:
            channel = discord.utils.get(interaction.guild.channels, id=c)
            await channel.purge(limit=100, check=is_me)

        for category in categories:
            server_list = await discord_server_lists.get_servers_for_category(category['id'])
            channel = discord.utils.get(
                interaction.guild.channels, id=category['channel_id'])

            list_of_servers = [server_list[i:i+10]
                               for i in range(0, len(server_list), 10)]

            for idx, servers in enumerate(list_of_servers):
                msgs = [
                    f"**__{category['category_title']}__**" if len(
                        list_of_servers) == 1 else f"**__{category['category_title']} - Part {idx+1}__**"
                ]
                msgs += [f"{s['server_description']}: https://discord.gg/{s['invite_id']}" for s in servers]
                await channel.send('\n'.join(msgs))

        await interaction.followup.send(f"Refreshed server list for {interaction.guild.name}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(DiscordServers(bot))
