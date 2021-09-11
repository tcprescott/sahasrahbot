from alttprbot.tournament.core import TournamentConfig
from alttprbot.tournament.sgl21 import ALTTPRQuals as Tournament
from alttprbot_discord.bot import discordbot


class TestTournament(Tournament):
    async def configuration(self):
        guild = discordbot.get_guild(508335685044928540)
        return TournamentConfig(
            guild=guild,
            racetime_category='test',
            racetime_goal='Beat the game',
            event_slug="test"
        )

    @property
    def announce_channel(self):
        return discordbot.get_channel(508335685044928548)