from alttprbot.tournament.dailies.core import SGDailyRaceCore
from alttprbot.tournament import event_settings


class SMZ3DailyRace(SGDailyRaceCore):
    async def configuration(self):
        return event_settings.tournament_config("smz3")

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

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=False,
            unlisted=False,
            info_user=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=True if self.friendly_name.lower().find("co-op") >= 0 else False,
        )
        return self.rtgg_handler
