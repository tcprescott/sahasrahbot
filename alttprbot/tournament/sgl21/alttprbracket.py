
import logging
import random

from alttprbot import models
from alttprbot.alttprgen.preset import generate_preset, fetch_preset
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace

class ALTTPRBrackets(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="A Link to the Past Randomizer",
            event_slug="sgl21alttpr",
            audit_channel=discordbot.get_channel(774336581808291863),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def roll(self):
        triforce_text = random.choice(await models.TriforceTexts.filter(broadcasted=False, pool_name='sglbracket'))

        if triforce_text is None:
            triforce_texts = random.choice(await models.TriforceTexts.filter(pool_name='sglbracket'))
            triforce_text = random.choice(triforce_texts)

        text = triforce_text.text.encode("utf-8").decode("unicode_escape")

        self.preset_dict = await fetch_preset('sglive')
        self.preset_dict['settings']['texts'] = {}
        self.preset_dict['settings']['texts']['end_triforce'] = "{NOBORDER}\n{SPEED6}\n" + text + "\n{PAUSE9}"
        self.seed = await generate_preset(self.preset_dict, hints=False, nohints=True, spoilers='off', tournament=True)

        triforce_text.broadcasted = True
        await triforce_text.save()

    @property
    def seed_info(self):
        return f"{self.seed.url} - {self.seed.code}"