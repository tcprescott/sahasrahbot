import aiohttp

from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace


class Timespinner(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Timespinner Randomizer",
            event_slug="sgl21timespinner",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def roll(self):
        async with aiohttp.request(url='https://tsrandomizerseedgenerator.azurewebsites.net/generate/json',
                                   method='get', raise_for_status=True) as req:
            self.seed = await req.json()

    @property
    def seed_info(self):
        return f"Seed: {self.seed['Seed']}"
