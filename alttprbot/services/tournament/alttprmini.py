"""``ALTTPRMiniOrchestrator`` — the ALTTPR Deutschland Mini tournament, decomposed.

Mirrors the legacy ``alttprmini.ALTTPRMiniTournament`` (extends the ALTTPR family,
overrides only ``roll()`` + ``configuration()``): the preset is chosen from the match
title via ``ALTTPRMINI_TITLE_MAP`` (shared parse in ``_roll_from_title_map``). Hardcoded
IDs move into ``ALTTPRMINI_DEFINITION``.
"""

from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

ALTTPRMINI_TITLE_MAP = {
    "Casual Boots": "casualboots",
    "6/6 Defeat Ganon": "nightcl4w/6_6_defeat_ganon",
    "Boss Shuffle": "nightcl4w/boss_shuffle",
    "Big Key Shuffle": "catobat/bkshuffle",
    "All Dungeons": "adboots",
}

ALTTPRMINI_DEFINITION = TournamentDefinition(
    event_slug="alttprmini",
    racetime_category="alttpr",
    racetime_goal="Beat the game",
    guild_id=469300113290821632,
    audit_channel_id=473668481011679234,
    commentary_channel_id=469317757331308555,
    helper_role_ids=[534030648713674765, 469300493542490112, 623071415129866240],
    lang="de",
)


class ALTTPRMiniOrchestrator(ALTTPRTournamentOrchestrator):
    async def roll(self) -> SeedResult:
        return await self._roll_from_title_map(
            ALTTPRMINI_TITLE_MAP, hints=False, spoilers="off", allow_quickswap=True
        )
