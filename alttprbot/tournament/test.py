from alttprbot.tournament import alttpr
from alttprbot.tournament.core import TournamentConfig
# from alttprbot.tournament import alttprleague
from alttprbot.services import bots


class TestTournament(alttpr.ALTTPR2024Race):
    async def configuration(self):
        guild = bots.discord().get_guild(508335685044928540)
        return TournamentConfig(
            guild=guild,
            racetime_category='test',
            racetime_goal='Beat the game',
            event_slug="test",
            audit_channel=bots.discord().get_channel(537469084527230976),
            # commentary_channel=bots.discord().get_channel(659307060499972096),
            # scheduling_needs_channel=bots.discord().get_channel(835699086261747742),
            # create_scheduled_events=True
        )

    @property
    def announce_channel(self):
        return bots.discord().get_channel(508335685044928548)

    @property
    def race_room_log_channel(self):
        return bots.discord().get_channel(537469084527230976)

    # @property
    # def announce_channel(self):
    #     return bots.discord().get_channel(508335685044928548)
