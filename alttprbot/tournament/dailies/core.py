import dataclasses
import datetime

from alttprbot import models
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot.util import speedgaming
from alttprbot_discord.bot import discordbot
from alttprbot_racetime import bot as racetime


class SGDailyRaceCore(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(307860211333595146)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game - Casual',
            event_slug="alttprdaily"
        )

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

    @property
    def player_racetime_ids(self):
        return []

    @property
    def race_info(self):
        msg = "SpeedGaming Daily Race Series - {title} at {start_time} Eastern".format(
            title=self.friendly_name,
            start_time=self.string_time(self.race_start_time)
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Seed Distributed at {seed_time} Eastern".format(
            seed_time=self.seed_time.astimezone(self.timezone).strftime("%-I:%M %p"),
        )
        msg += f" - {self.episodeid}"
        return msg

    @property
    def seed_time(self):
        return self.race_start_time - datetime.timedelta(minutes=10)

    def room_opened_event(self):
        # The announcement itself is posted by alttprbot_discord/notifications.py.
        return dataclasses.replace(super().room_opened_event(), seed_time=self.seed_time)

    async def update_data(self, update_episode=True):
        self.episode = await speedgaming.get_episode(self.episodeid)

        self.tournament_game = await models.TournamentGames.get_or_none(episode_id=self.episodeid)

        self.rtgg_bot: racetime.SahasrahBotRaceTimeBot = racetime.racetime_bots[self.data.racetime_category]
        self.restream_team = await self.rtgg_bot.get_team('sg-volunteers')
