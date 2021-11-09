from alttprbot.tournament.core import TournamentConfig
# from alttprbot.tournament import sgl21
from alttprbot.tournament import alttprleague
from alttprbot_discord.bot import discordbot


class TestTournament(alttprleague.ALTTPRLeague):
    async def configuration(self):
        guild = discordbot.get_guild(508335685044928540)
        return TournamentConfig(
            guild=guild,
            racetime_category='test',
            racetime_goal='Beat the game',
            event_slug="test",
            audit_channel=discordbot.get_channel(537469084527230976),
            commentary_channel=discordbot.get_channel(659307060499972096)
        )

    # @property
    # def race_room_log_channel(self):
    #     return discordbot.get_channel(678695059016646697)

    # @property
    # def announce_channel(self):
    #     return discordbot.get_channel(508335685044928548)
