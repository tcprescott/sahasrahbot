from alttprbot.alttprgen.generator import ALTTPRPreset
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot.alttprgen import preset
from alttprbot_discord.bot import discordbot

ALTTPRMINI_TITLE_MAP = {
    'Open Deutscher Hard Pool': 'derduden2/german_hard',
    'Open 6/6 Fast Ganon': 'open_fast_66',
    'Open All Dungeons': 'dungeons',
    'Standard': 'standard',
    'Casual Boots': 'casualboots',
    'Boss Shuffle': 'enemizer_bossesonly',
    'Enemy Shuffle Assured': 'teto/enemizer_assured',
    'Big Key Shuffle': 'catobat/bkshuffle',
    'Keysanity': 'keysanity',
}


class ALTTPRMiniTournament(ALTTPRTournamentRace):
    async def roll(self):
        try:
            preset = ALTTPRMINI_TITLE_MAP[self.episode['match1']['title']]
        except KeyError:
            await self.rtgg_handler.send_message("Invalid mode chosen, please contact a tournament admin for assistance.")
            raise
        self.seed = await ALTTPRPreset(preset).generate(hints=False, spoilers="off", allow_quickswap=True)

    async def configuration(self):
        guild = discordbot.get_guild(469300113290821632)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprmini",
            audit_channel=discordbot.get_channel(473668481011679234),
            commentary_channel=discordbot.get_channel(469317757331308555),
            helper_roles=[
                guild.get_role(534030648713674765),
                guild.get_role(469300493542490112),
                guild.get_role(623071415129866240),
            ],
            lang='de',
            stream_delay=10,
            gsheet_id='1dWzbwxoErGQyO4K1tZ-EexX1bdnTGuxQhLJDnmfcaR4',
        )
