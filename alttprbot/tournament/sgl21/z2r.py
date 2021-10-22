import random

from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace


class Z2R(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Zelda 2 Randomizer",
            event_slug="sgl21zelda2",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def roll(self):
        self.seed = random.randint(0, 1000000000)

    @property
    def seed_info(self):
        return f"Seed: {self.seed} - Flags: jhhhD0j9$78$JpTBT!BhSA!0P@@A"
