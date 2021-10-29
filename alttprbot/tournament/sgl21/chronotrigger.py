from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from alttprbot.alttprgen import generator
from .sglcore import SGLRandomizerTournamentRace


class CTJets(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Chrono Trigger Jets of Time",
            event_slug="sgl21ctjets",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def roll(self):
        self.seed = await generator.CTJetsPreset('sglive').generate()

    @property
    def seed_info(self):
        return self.seed