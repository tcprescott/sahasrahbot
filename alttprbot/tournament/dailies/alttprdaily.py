from alttprbot.tournament.dailies.core import SGDailyRaceCore
from alttprbot.tournament import event_settings


class AlttprSGDailyRace(SGDailyRaceCore):
    async def configuration(self):
        return event_settings.tournament_config("alttprdaily")

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
