import json

import aiohttp
import discord
from discord.ext import commands

from alttprbot import models


class RacetimeTools(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_racetime_open(self, handler, data):
        pass

    @commands.Cog.listener()
    async def on_racetime_invitational(self, handler, data):
        pass

    @ commands.Cog.listener()
    async def on_racetime_in_progress(self, handler, data):
        await self.watchlisted_players(handler)
        await self.new_players(handler)

    @ commands.Cog.listener()
    async def on_racetime_cancelled(self, handler, data):
        pass

    @ commands.Cog.listener()
    async def on_racetime_finished(self, handler, data):
        pass

    async def watchlisted_players(self, handler):
        entrant_ids = [a['user']['id'] for a in handler.data['entrants']]
        watchlisted_players = await models.RTGGWatcherPlayer.filter(racetime_id__in=entrant_ids, rtgg_watcher__category=handler.bot.category_slug).prefetch_related("rtgg_watcher")
        for watchlisted_player in watchlisted_players:
            channel = self.bot.get_channel(watchlisted_player.rtgg_watcher.channel_id)
            player_data_uri = handler.bot.http_uri(f"/user/{watchlisted_player.racetime_id}/data")
            race_room_uri = handler.bot.http_uri(handler.data['url'])

            async with aiohttp.request(method='get', url=player_data_uri, raise_for_status=True) as resp:
                user_data = json.loads(await resp.read())

            player_profile_uri = handler.bot.http_uri(user_data['url'])

            embed = discord.Embed(
                title="Watchlisted Player Detected in race",
                description=f"Watchlisted player [{user_data['full_name']}]({player_profile_uri}) began racing in [{handler.data.get('name')}]({race_room_uri})",
                color=discord.Colour.red()
            )
            await channel.send(embed=embed)

    async def new_players(self, handler):
        entrant_ids = [a['user']['id'] for a in handler.data['entrants']]
        watchers = await models.RTGGWatcher.filter(category=handler.bot.category_slug)
        for watcher in watchers:
            channel = self.bot.get_channel(watcher.channel_id)
            if not watcher.notify_on_new_player:
                continue

            for entrant in entrant_ids:
                player_data_uri = handler.bot.http_uri(f"/user/{entrant}/data")
                async with aiohttp.request(method='get', url=player_data_uri, raise_for_status=True) as resp:
                    user_data = json.loads(await resp.read())
                    player_profile_uri = handler.bot.http_uri(user_data['url'])
                    race_room_uri = handler.bot.http_uri(handler.data['url'])

                    if user_data['stats']['joined'] == 0:
                        embed = discord.Embed(
                            title="New Racer Detected!",
                            description=f"A new racer named [{user_data['full_name']}]({player_profile_uri}) began racing in [{handler.data.get('name')}]({race_room_uri})",
                            color=discord.Colour.green()
                        )
                        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RacetimeTools(bot))
