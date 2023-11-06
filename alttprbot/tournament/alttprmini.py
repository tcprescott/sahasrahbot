from alttprbot.alttprgen.generator import ALTTPRPreset
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot


class ALTTPRMiniTournament(ALTTPRTournamentRace):
    async def roll(self):
        self.seed = await ALTTPRPreset("nightcl4w/duality").generate(tournament=True, spoilers="off")

    async def configuration(self):
        guild = discordbot.get_guild(469300113290821632)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game (assisted)',
            event_slug="alttprmini",
            audit_channel=discordbot.get_channel(473668481011679234),
            commentary_channel=discordbot.get_channel(469317757331308555),
            helper_roles=[
                guild.get_role(534030648713674765),
                guild.get_role(469300493542490112),
                guild.get_role(623071415129866240),
            ],
            lang='de',
            # stream_delay=10,
            gsheet_id='1dWzbwxoErGQyO4K1tZ-EexX1bdnTGuxQhLJDnmfcaR4',
            coop=True,
        )
