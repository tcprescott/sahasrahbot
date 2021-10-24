import discord
from discord.ext import commands

from alttprbot.database import discord_server_lists # TODO switch to ORM


class DiscordServers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=['dg'])
    @commands.is_owner()
    async def discordservers(self, ctx):
        pass

    @discordservers.group()
    @commands.is_owner()
    async def category(self, ctx):
        pass

    @category.command(name='add')
    @commands.is_owner()
    async def category_add(self, ctx, channel: commands.TextChannelConverter, category_title, category_description=None, order=0):
        await discord_server_lists.add_category(ctx.guild.id, channel.id, category_title=category_title, category_description=category_description, order=order)

    @category.command(name='list')
    @commands.is_owner()
    async def category_list(self, ctx):
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
            await ctx.reply(embed=embed)

    @category.command(name='remove')
    @commands.is_owner()
    async def category_remove(self, ctx, category_id: int):
        await discord_server_lists.remove_category(ctx.guild.id, category_id)

    @category.command(name='update')
    @commands.is_owner()
    async def category_update(self, ctx, category_id: int, category_title, category_description=None, order=0):
        await discord_server_lists.update_category(category_id, ctx.guild.id, category_title, category_description, order)

    @discordservers.group()
    @commands.is_owner()
    async def server(self, ctx):
        pass

    @server.command(name='add')
    @commands.is_owner()
    async def server_add(self, ctx, category_id: int, invite: commands.InviteConverter, server_description=None):
        await discord_server_lists.add_server(ctx.guild.id, invite.id, category_id, server_description=server_description)

    @server.command(name='list')
    @commands.is_owner()
    async def server_list(self, ctx, category_id: int):
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
            await ctx.reply(embed=embed)

    @server.command(name='remove')
    @commands.is_owner()
    async def server_remove(self, ctx, server_id: int):
        await discord_server_lists.remove_server(ctx.guild.id, server_id)

    @server.command(name='update')
    @commands.is_owner()
    async def server_update(self, ctx, server_id: int, invite: commands.InviteConverter, category_id: int, server_description=None):
        await discord_server_lists.update_server(ctx.guild.id, server_id, invite.id, category_id, server_description)

    @discordservers.command()
    @commands.is_owner()
    async def refresh(self, ctx):
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


def setup(bot):
    bot.add_cog(DiscordServers(bot))
