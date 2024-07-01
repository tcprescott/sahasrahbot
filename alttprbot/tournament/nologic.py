from alttprbot.alttprgen import generator
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot


class ALTTPRNoLogicRace(ALTTPRTournamentRace):
    async def roll(self):
        self.seed = await generator.ALTTPRPreset('nologic_rods').generate(allow_quickswap=True, branch='beeta')

    async def configuration(self):
        guild = discordbot.get_guild(535946014037901333)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game (glitched)',
            event_slug="nologic",
            lang='en',
            audit_channel=discordbot.get_channel(850226062864023583),
            commentary_channel=discordbot.get_channel(549709098015391764),
        )
