from alttprbot.alttprgen.randomizer import roll_z1r
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace

class Z1R(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Zelda 1 Randomizer",
            event_slug="sgl21z1r",
            audit_channel=discordbot.get_channel(774336581808291863),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def roll(self):
        self.seed_id, self.flags = roll_z1r('VlWlIEwJ1MsKm8TdWgb5iC2DDmd8WW')

    @property
    def seed_info(self):
        return f"Seed: {self.seed_id} - Flags: {self.flags}"