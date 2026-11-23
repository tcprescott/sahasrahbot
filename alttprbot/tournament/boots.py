from alttprbot.alttprgen import generator
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot.services import bots


class ALTTPRCASBootsTournamentRace(ALTTPRTournamentRace):
    async def roll(self):
        self.seed = await generator.ALTTPRPreset('casualboots').generate(allow_quickswap=True)

    async def configuration(self):
        guild = bots.discord().get_guild(973765801528139837)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game - Tournament (Solo)',
            event_slug="boots",
            lang='en'
        )
