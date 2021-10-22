import os

import aiohttp
import discord

from alttprbot.tournament.dailies.core import SGDailyRaceCore, TournamentConfig
from alttprbot_discord.bot import discordbot

SG_DISCORD_WEBHOOK = os.environ.get('SG_DISCORD_WEBHOOK', None)


class AlttprSGDailyRace(SGDailyRaceCore):
    async def configuration(self):
        guild = discordbot.get_guild(307860211333595146)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprdaily",
            room_open_time=60
        )

    @property
    def announce_channel(self):
        return discordbot.get_channel(307861467838021633)

    @property
    def announce_message(self):
        msg = "SpeedGaming Daily Race Series - {title} at {start_time} ({start_time_remain})".format(
            title=self.friendly_name,
            start_time=self.discord_time(self.race_start_time),
            start_time_remain=self.discord_time(self.race_start_time, "R")
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Seed Distributed {seed_time} - {racetime_url}".format(
            seed_time=self.discord_time(self.seed_time, "R"),
            racetime_url=self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])
        )
        return msg

    @property
    def race_info(self):
        msg = "SpeedGaming Daily Race Series - {title} at {start_time} Eastern".format(
            title=self.friendly_name,
            start_time=self.string_time(self.race_start_time)
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Seed Distributed at {seed_time} Eastern".format(
            seed_time=self.string_time(self.seed_time),
        )
        msg += f" - {self.episodeid}"
        return msg

    async def send_player_room_info(self):
        await self.announce_channel.send(
            content=self.announce_message,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(SG_DISCORD_WEBHOOK, adapter=discord.AsyncWebhookAdapter(session))
            await webhook.send(f"<@&399038388964950016> {self.announce_message}", username="SahasrahBot")
