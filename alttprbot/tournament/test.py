from alttprbot.tournament.alttprfr import ALTTPRFRTournament
import logging

import discord
from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.alttprfr import ALTTPRFRTournament
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot_discord.bot import discordbot


class TestTournament(ALTTPRFRTournament):
    async def configuration(self):
        guild = discordbot.get_guild(508335685044928540)
        return TournamentConfig(
            guild=guild,
            racetime_category='test',
            racetime_goal='Beat the game',
            event_slug="test",
            audit_channel=discordbot.get_channel(537469084527230976),
            commentary_channel=discordbot.get_channel(659307060499972096),
            helper_roles=[
                guild.get_role(523276397679083520),
            ]
        )
