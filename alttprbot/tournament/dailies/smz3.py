from alttprbot.tournament.dailies.core import SGDailyRaceCore, TournamentConfig
from alttprbot_discord.bot import discordbot


class SMZ3DailyRace(SGDailyRaceCore):
    async def configuration(self):
        guild = discordbot.get_guild(445948207638511616)
        return TournamentConfig(
            guild=guild,
            racetime_category='smz3',
            racetime_goal='Beat the games',
            event_slug="smz3"
        )

    @property
    def announce_channel(self):
        return discordbot.get_channel(451977523123978260)

    @property
    def announce_message(self):
        msg = "<@&449260882501959700> SMZ3 Weekly Race - {title} at {start_time} ({start_time_remain})".format(
            title=self.friendly_name,
            start_time=self.discord_time(self.race_start_time),
            start_time_remain=self.discord_time(self.race_start_time, "R")
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - {racetime_url}".format(
            racetime_url=self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])
        )

        return msg

    @property
    def race_info(self):
        msg = "SMZ3 Weekly Race - {title} at {start_time} Eastern".format(
            title=self.friendly_name,
            start_time=self.string_time(self.race_start_time)
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += f" - {self.episodeid}"
        return msg
