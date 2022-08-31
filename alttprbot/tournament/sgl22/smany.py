import os

from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLCoreTournamentRace


class SMAny(SGLCoreTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="SM Any%",
            event_slug="sgl22smany",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET"),
            auto_record=True
        )
