import os

from alttprbot.alttprgen.randomizer import roll_smb3r
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace


class SMB3R(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Super Mario Bros. 3 Randomizer",
            event_slug="sgl21smb3r",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET"),
            auto_record=True
        )

    @property
    def seed_info(self):
        return f"Seed: {self.seed_id} - Flags: {self.flags}"

    async def roll(self):
        self.seed_id, self.flags = roll_smb3r('17BCWYIUA4')
