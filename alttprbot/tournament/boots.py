from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot.alttprgen import preset
from alttprbot_discord.bot import discordbot


class ALTTPRCASBootsTournamentRace(ALTTPRTournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('casualboots')

    async def configuration(self):
        guild = discordbot.get_guild(973765801528139837)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="boots",
            lang='en'
        )
