import logging
import random
import os

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
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            stream_delay=20,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET"),
            auto_record=True
        )

    async def roll(self):
        try:
            if self.broadcast_channels:
                triforce_texts = await models.TriforceTexts.filter(broadcasted=False, pool_name='sglfinal')
            else:
                triforce_texts = await models.TriforceTexts.filter(pool_name='sglfinal')

            if not triforce_texts:
                triforce_texts = await models.TriforceTexts.filter(pool_name='sglfinal')

            triforce_text = random.choice(triforce_texts)

            text = triforce_text.text.encode("utf-8").decode("unicode_escape")

            logging.info(f"Using triforce text: {text}")

            self.preset_dict = await fetch_preset('sglive')
            self.preset_dict['settings']['texts'] = {}
            self.preset_dict['settings']['texts']['end_triforce'] = "{NOBORDER}\n{SPEED6}\n" + text + "\n{PAUSE9}"
            self.seed = await generate_preset(self.preset_dict, hints=False, nohints=True, spoilers='off', tournament=True)

            if self.broadcast_channels:
                triforce_text.broadcasted = True
                await triforce_text.save()
        except IndexError:
            logging.exception("Could not retrieve any triforce texts, generating this normally instead...")
            self.preset_dict = await fetch_preset('sglive')
            self.seed = await generate_preset(self.preset_dict, hints=False, nohints=True, spoilers='off', tournament=True)

    @property
    def seed_code(self):
        return f"({'/'.join(self.seed.code)})"

    @property
    def seed_info(self):
        return f"{self.seed.url} - {self.seed_code}"
