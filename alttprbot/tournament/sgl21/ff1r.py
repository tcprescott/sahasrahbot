from alttprbot.alttprgen.randomizer import roll_ffr
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace
import os


class FFR(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Final Fantasy 1 Randomizer",
            event_slug="sgl21ffr",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            stream_delay=15,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET")
        )

    async def roll(self):
        _, self.seed_url = roll_ffr("https://4-2-3.finalfantasyrandomizer.com/?s=0&f=YerhiLJ4MsRAxHLfsmtgvEUakmYRfqHbd44FvmfJi8HqCr4fd7TUBGkjKSytIkmBrpcKfJBbWCXHhJOG7GWir-U2V6hGfHEAxuNEiePNZlKdoymWRgmehZgLdXjVqCEGjOS9akIwEx2bSd9tB")

    @property
    def seed_info(self):
        return self.seed_url
