from alttprbot.tournament import alttpr, event_settings


class TestTournament(alttpr.ALTTPR2024Race):
    async def configuration(self):
        return event_settings.tournament_config("test")
