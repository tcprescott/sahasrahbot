from alttprbot.tournament import alttpr, settings


class TestTournament(alttpr.ALTTPR2024Race):
    async def configuration(self):
        return settings.tournament_config("test")
