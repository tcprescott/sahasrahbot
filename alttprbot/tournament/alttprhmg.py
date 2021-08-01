from alttprbot.tournament.core import TournamentRace
from alttprbot.alttprgen import preset

class ALTTPRHMGTournament(TournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('hybridmg')
        await self.create_embeds()
