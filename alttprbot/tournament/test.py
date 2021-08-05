from alttprbot.tournament.alttprfr import ALTTPRFRTournament
import logging

import discord
from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.alttprfr import ALTTPRFRTournament
from alttprbot.tournament.alttpres import ALTTPRESTournament
from alttprbot.tournament.alttprhmg import ALTTPRHMGTournament
from alttprbot.tournament.smz3coop import SMZ3CoopTournament
from alttprbot.tournament.alttprdaily import AlttprSGDailyRace
from alttprbot.tournament.smz3 import SMZ3DailyRace
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

    @property
    def announce_channel(self):
        return discordbot.get_channel(508335685044928548)