# import random

# from alttprbot import models
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLCoreTournamentRace


class TWWR(SGLCoreTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='twwr',
            racetime_goal="Spoiler Log Race",
            event_slug="sgl21twwr",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            stream_delay=60
        )

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=False,
            unlisted=False,
            info=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=False,
            auto_start=False,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=False,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=False,
        )
        return self.rtgg_handler

    @property
    def race_info(self):
        return f"SGL 2021 - {self.notes} - {self.versus}"

    @property
    def notes(self):
        if self.friendly_name == '':
            return self.episode['match1']['note']

        return self.friendly_name
