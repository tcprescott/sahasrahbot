from alttprbot.tournament.alttprfr import ALTTPRFRTournament
import logging

import discord
from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.alttprfr import ALTTPRFRTournament
from alttprbot.tournament.alttpres import ALTTPRESTournament
from alttprbot.tournament.alttprhmg import ALTTPRHMGTournament
from alttprbot.tournament.smz3coop import SMZ3CoopTournament
from alttprbot.tournament.smbingo import SMBingoTournament
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot_discord.bot import discordbot


class TestTournament(SMBingoTournament):
    async def configuration(self):
        guild = discordbot.get_guild(508335685044928540)
        return TournamentConfig(
            guild=guild,
            racetime_category='test',
            racetime_goal='Beat the game',
            event_slug="test",
            audit_channel=discordbot.get_channel(537469084527230976),
            commentary_channel=discordbot.get_channel(659307060499972096),
            scheduling_needs_channel=discordbot.get_channel(835699086261747742),
            scheduling_needs_tracker=True,
            helper_roles=[
                guild.get_role(523276397679083520),
            ]
        )

    async def create_race_room(self, goal, info, team_race=False):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=goal,
            invitational=True,
            unlisted=False,
            info=info,
            start_delay=15,
            time_limit=24,
            streaming_required=False,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=team_race,
        )
        return self.rtgg_handler