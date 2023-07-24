import discord

from alttprbot.tournament.dailies.core import SGDailyRaceCore, TournamentConfig
from alttprbot_discord.bot import discordbot


class SMZ3DailyRace(SGDailyRaceCore):
    async def configuration(self):
        guild = discordbot.get_guild(445948207638511616)
        return TournamentConfig(
            guild=guild,
            racetime_category='smz3',
            racetime_goal='Beat the games',
            event_slug="smz3",
            room_open_time=60
        )

    @property
    def announce_channel(self):
        return discordbot.get_channel(451977523123978260)

    @property
    def announce_message(self):
        msg = "<@&449260882501959700> SMZ3 Weekly Race - {title} - {start_time} ({start_time_remain})".format(
            title=self.friendly_name,
            start_time=discord.utils.format_dt(self.race_start_time),
            start_time_remain=discord.utils.format_dt(self.race_start_time, "R")
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

    async def create_race_room(self):
        if self.friendly_name.lower().find("spoiler") >= 0:
            racetime_goal = "Beat the Games(Spoiler Log)"
        else:
            racetime_goal = self.data.racetime_goal

        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=racetime_goal,
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
