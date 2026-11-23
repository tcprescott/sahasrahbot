from alttprbot.tournament.dailies.core import SGDailyRaceCore, TournamentConfig
from alttprbot.services import bots


class AlttprSGDailyRace(SGDailyRaceCore):
    async def configuration(self):
        guild = bots.discord().get_guild(307860211333595146)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game - Casual',
            event_slug="alttprdaily",
            room_open_time=60
        )

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
