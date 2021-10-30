from alttprbot.alttprgen.randomizer import ssr
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot

from .sglcore import SGLRandomizerTournamentRace


class SSR(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Skyward Sword Randomizer",
            event_slug="sgl21ssr",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            stream_delay=15
        )

    async def roll(self):
        self.seed = await ssr.generate_seed(
            permalink="IQ0IIDsD85rpUwAAAAAAACHIFwA=",
            spoiler=False
        )

    @property
    def seed_info(self):
        return f"Seed: {self.seed.seed}, Hash: {self.seed.hash}, Permalink: {self.seed.permalink}, Version: {self.seed.version}"
