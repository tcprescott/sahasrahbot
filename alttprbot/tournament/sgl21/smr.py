import os

from alttprbot_discord.util.smvaria_discord import SuperMetroidVariaDiscord
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace


class SuperMetroidRando(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Super Metroid Randomizer",
            event_slug="sgl21smr",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET")
        )

    async def roll(self):
        self.seed = await SuperMetroidVariaDiscord.create(
            settings_preset="SGLive2021",
            skills_preset="Season_Races",
            race=True
        )

    @property
    def seed_info(self):
        return self.seed.url
