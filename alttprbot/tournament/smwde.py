from alttprbot.tournament.core import TournamentRace, TournamentConfig
from alttprbot_discord.bot import discordbot


class SMWDETournament(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(753727862229565612)
        return TournamentConfig(
            guild=guild,
            racetime_category='smw-hacks',
            racetime_goal='Any%',
            event_slug="smwde",
            audit_channel=discordbot.get_channel(826775494329499648),
            scheduling_needs_channel=discordbot.get_channel(835946387065012275),
            helper_roles=[
                guild.get_role(754845429773893782),
                guild.get_role(753742980820631562),
            ],
            lang='de',
            gsheet_id='1BrkmhNPnpjNUSUx5yGrnm09XbfAFhYDsi-7-fHp62qY',
        )
