from importlib.metadata import requires
import discord
from discord.commands import permissions, ApplicationContext, Option
from discord.ext import commands

from alttprbot.database import discord_server_lists  # TODO switch to ORM


class DiscordServers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    discordservers = discord.commands.SlashCommandGroup(
        "discordservers",
        "Commands for updating the discord server list.",
        permissions=[
            permissions.CommandPermission(
                "owner", 2, True
            )
        ]
    )

    category = discordservers.create_subgroup("category", "Manage catagories.")

    @category.command(name='add')
    async def category_add(self, ctx: ApplicationContext, channel: Option(discord.TextChannel, required=True), category_title: Option(str), category_description: Option(str, default=None), order=Option(int, default=0)):
        await discord_server_lists.add_category(ctx.guild.id, channel.id, category_title=category_title, category_description=category_description, order=order)
        await ctx.respond(f"Added category {category_title} to {channel.mention}", ephemeral=True)

    @category.command(name='list')
    async def category_list(self, ctx: ApplicationContext):
        results = await discord_server_lists.get_categories(ctx.guild.id)
        if results:
            embed = discord.Embed(
                title="List of categories",
                color=discord.Colour.blue(),
            )
            for result in results:
                channel = ctx.guild.get_channel(result['channel_id'])
                embed.add_field(
                    name=result['category_title'],
                    value=f"_*Id:*_ {result['id']}\n_*Channel:*_ {channel.mention}",
                    inline=False
                )
            await ctx.respond(embed=embed)

    @category.command(name='remove')
    async def category_remove(self, ctx: ApplicationContext, category_id: Option(int, required=True)):
        await discord_server_lists.remove_category(ctx.guild.id, category_id)
        await ctx.respond(f"Removed category {category_id}", ephemeral=True)

    @category.command(name='update')
    async def category_update(self, ctx: ApplicationContext, category_id: Option(int, required=True), category_title: Option(str), category_description: Option(str, default=None), order=Option(int, default=0)):
        await discord_server_lists.update_category(category_id, ctx.guild.id, category_title, category_description, order)
        await ctx.respond(f"Updated category {category_id}", ephemeral=True)

    server = discordservers.create_subgroup("server", "Manage servers in a category.")

    @server.command(name='add')
    async def server_add(self, ctx, category_id: Option(int, required=True), invite: discord.Invite, server_description: str):
        await discord_server_lists.add_server(ctx.guild.id, invite.id, category_id, server_description=server_description)
        await ctx.respond(f"Added server {invite.guild.name} to category {category_id}", ephemeral=True)

    @server.command(name='list')
    async def server_list(self, ctx: ApplicationContext, category_id: int):
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
            await ctx.respond(embed=embed)

    @server.command(name='remove')
    async def server_remove(self, ctx, server_id: int):
        await discord_server_lists.remove_server(ctx.guild.id, server_id)
        await ctx.respond(f"Removed server {server_id}", ephemeral=True)

    @server.command(name='update')
    async def server_update(self, ctx, server_id: int, invite: discord.Invite, category_id: int, server_description: str = None):
        await discord_server_lists.update_server(ctx.guild.id, server_id, invite.id, category_id, server_description)
        await ctx.respond(f"Updated server {server_id}", ephemeral=True)

    @discordservers.command()
    async def refresh(self, ctx):
        await ctx.defer()

        def is_me(m):
            return m.author == self.bot.user

        categories = await discord_server_lists.get_categories(ctx.guild.id)
        channels_to_update = list(set([c['channel_id'] for c in categories]))

        for c in channels_to_update:
            channel = discord.utils.get(ctx.guild.channels, id=c)
            await channel.purge(limit=100, check=is_me)

        for category in categories:
            server_list = await discord_server_lists.get_servers_for_category(category['id'])
            channel = discord.utils.get(
                ctx.guild.channels, id=category['channel_id'])

            list_of_servers = [server_list[i:i+10]
                               for i in range(0, len(server_list), 10)]

            for idx, servers in enumerate(list_of_servers):
                msgs = [
                    f"**__{category['category_title']}__**" if len(
                        list_of_servers) == 1 else f"**__{category['category_title']} - Part {idx+1}__**"
                ]
                msgs += [f"{s['server_description']}: https://discord.gg/{s['invite_id']}" for s in servers]
                await channel.send('\n'.join(msgs))

        await ctx.respond(f"Refreshed server list for {ctx.guild.name}", ephemeral=True)


def setup(bot):
    bot.add_cog(DiscordServers(bot))
