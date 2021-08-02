from alttprbot.alttprgen import preset
from alttprbot.tournament.core import TournamentConfig
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot_discord.bot import discordbot

class SMZ3CoopTournament(ALTTPRTournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('hard', tournament=True, randomizer='smz3')
        await self.create_embeds()

    async def configuration(self):
        guild = discordbot.get_guild(460905692857892865)
        return TournamentConfig(
            guild=guild,
            racetime_category='smz3',
            racetime_goal='Beat the games',
            event_slug="smz3coop",
            audit_channel=discordbot.get_channel(516808047935619073),
            commentary_channel=discordbot.get_channel(687471466714890296),
            scheduling_needs_channel=discordbot.get_channel(864249492370489404),
            scheduling_needs_tracker=True,
            helper_roles=[
                guild.get_role(464497534631542795),
            ]
        )

    @property
    def seed_code(self):
        return f"({self.seed.code})"
