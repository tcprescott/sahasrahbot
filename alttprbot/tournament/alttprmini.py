from alttprbot.alttprgen.generator import ALTTPRPreset
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot

ALTTPRMINI_TITLE_MAP = {
    'Casual Boots': 'casualboots',
    '6/6 Defeat Ganon': 'nightcl4w/6_6_defeat_ganon',
    'Boss Shuffle': 'nightcl4w/boss_shuffle',
    'Big Key Shuffle': 'catobat/bkshuffle',
    'All Dungeons': 'adboots',
}

class ALTTPRMiniTournament(ALTTPRTournamentRace):
    async def roll(self):
        try:
            match_title = self.episode['match1']['title']
            # we need to strip out anything before the : in the title
            match_title = match_title.split(':')[-1].strip()
            preset = ALTTPRMINI_TITLE_MAP[match_title]
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
            event_slug="alttprmini",
            audit_channel=discordbot.get_channel(473668481011679234),
            commentary_channel=discordbot.get_channel(469317757331308555),
            helper_roles=[
                guild.get_role(534030648713674765),
                guild.get_role(469300493542490112),
                guild.get_role(623071415129866240),
            ],
            lang='de',
            # stream_delay=10,
            coop=False,
        )
