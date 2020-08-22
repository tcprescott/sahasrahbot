import discord
from discord.ext import commands

from alttprbot.database.discord_server_list import get_categories, get_servers_for_category


class DiscordServers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def updatediscordservers(self, ctx):
        def is_me(m):
            return m.author == self.bot.user

        categories = await get_categories(ctx.guild.id)
        channels_to_update = list(set([c['channel_id'] for c in categories]))

        for c in channels_to_update:
            channel = discord.utils.get(ctx.guild.channels, id=c)
            await channel.purge(limit=100, check=is_me)

        for category in categories:
            server_list = await get_servers_for_category(category['id'])
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
