import os

from alttprbot.alttprgen.randomizer import roll_aosr
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace


class AOSR(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Aria of Sorrow Randomizer",
            event_slug="sgl21aosr",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET")
        )

    async def roll(self):
        self.seed_id, self.permalink = roll_aosr(
            logic='AreaTechTiers',
            nodupes='false',
            panther='FirstAlways',
            area='AreaRandom',
            boss='Dead-endShuffle',
            enemy='Vanilla',
            itempool='Standard',
            weight=2.5,
            grahm='BookSouls',
            kicker='false',
            startshop='Unlocked30k',
            shopprice='RandHV',
            shopSouls='Half',
            levelexp='Vanilla',
            telestart='false',
            mapassist='false',
            doublechaos='false'
        )

    @property
    def seed_info(self):
        return self.permalink
