# import copy
# import logging
# import random

# import discord
# from pyz3r.customizer import BASE_CUSTOMIZER_PAYLOAD
# from werkzeug.datastructures import MultiDict

# from alttprbot import models
from alttprbot.alttprgen.generator import ALTTPRPreset
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot

ALTTPRDE_TITLE_MAP = {
    'Open': 'open',
    'Standard': 'standard',
    '6/6 Fast Ganon': 'open_fast_66',
    'Casual Boots': 'casualboots',
    'Big Key Shuffle': 'catobat/bkshuffle',
    'Boss Shuffle': 'nightcl4w/german_boss_shuffle',
    'All Dungeons': 'adboots',
    'Open Hard': 'derduden2/german_hard',
    'Enemizer': 'enemizer',
    '6/6 Vanilla Swords': 'nightcl4w/6_6_vanilla_swords',
    'All Dungeons Keysanity': 'adkeys_boots',  
    'Standard Swordless': 'nightcl4w/german_swordless2024',
}

class ALTTPRDETournament(ALTTPRTournamentRace):
    async def roll(self):
        try:
            match_title = self.episode['match1']['title']
            # we need to strip out anything before the : in the title
            match_title = match_title.split(':')[-1].strip()
            preset = ALTTPRDE_TITLE_MAP[match_title]
        except KeyError:
            await self.rtgg_handler.send_message(
                "Invalid mode chosen, please contact a tournament admin for assistance.")
            raise
        self.seed = await ALTTPRPreset(preset).generate(hints=False, spoilers="off", allow_quickswap=True)

    async def configuration(self):
        guild = discordbot.get_guild(469300113290821632)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprde",
            audit_channel=discordbot.get_channel(473668481011679234),
            commentary_channel=discordbot.get_channel(469317757331308555),
            helper_roles=[
                guild.get_role(534030648713674765),
                guild.get_role(469300493542490112),
                guild.get_role(623071415129866240),
            ],
            lang='de',
            stream_delay=10,
            create_scheduled_events=True,
        )
