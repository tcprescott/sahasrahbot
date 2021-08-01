from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.alttprgen import preset

class ALTTPRCDTournament(ALTTPRTournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('crossedkeydrop')
        await self.create_embeds()
