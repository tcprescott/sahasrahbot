from alttprbot.tournament.core import TournamentConfig
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot_discord.bot import discordbot
from alttprbot.alttprgen import preset


class ALTTPRHMGTournament(ALTTPRTournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('hybridmg')

    async def configuration(self):
        guild = discordbot.get_guild(535946014037901333)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game (glitched)',
            event_slug="alttprhmg",
            audit_channel=discordbot.get_channel(850226062864023583),
            commentary_channel=discordbot.get_channel(549709098015391764),
            scheduling_needs_channel=discordbot.get_channel(863817206452977685),
            scheduling_needs_tracker=True,
            helper_roles=[
                guild.get_role(549709214000480276),
                guild.get_role(535962854004883467),
                guild.get_role(535962802230132737),
            ]
        )
