from alttprbot.tournament.sgdailies import TournamentConfig, SGDailyRaceCore
from alttprbot_discord.bot import discordbot


class AlttprSGDailyRace(SGDailyRaceCore):
    async def configuration(self):
        guild = discordbot.get_guild(307860211333595146)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprdaily"
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
        return msg
