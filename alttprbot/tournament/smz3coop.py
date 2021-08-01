import logging

import discord

from alttprbot.alttprgen import preset
from alttprbot import models
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord

class SMZ3CoopTournament(ALTTPRTournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('hard', tournament=True, randomizer='smz3')
        await self.create_embeds()

    @property
    def seed_code(self):
        return f"({self.seed.code})"
