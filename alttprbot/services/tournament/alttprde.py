"""``ALTTPRDEOrchestrator`` — the ALTTPR Deutschland tournament, decomposed.

Mirrors the legacy ``alttprde.ALTTPRDETournament`` (extends the ALTTPR family, overrides
only ``roll()`` + ``configuration()``): the preset is chosen from the match title via
``ALTTPRDE_TITLE_MAP`` (shared parse in ``_roll_from_title_map``). Hardcoded IDs move into
``ALTTPRDE_DEFINITION``.
"""

from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

ALTTPRDE_TITLE_MAP = {
    "Open": "open",
    "Standard": "standard",
    "6/6 Fast Ganon": "open_fast_66",
    "Casual Boots": "casualboots",
    "Big Key Shuffle": "catobat/bkshuffle",
    "Boss Shuffle": "nightcl4w/german_boss_shuffle",
    "All Dungeons": "adboots",
    "Open Hard": "derduden2/german_hard",
    "Enemizer": "enemizer",
    "6/6 Vanilla Swords": "nightcl4w/6_6_vanilla_swords",
    "All Dungeons Keysanity": "adkeys_boots",
    "Standard Swordless": "nightcl4w/german_swordless2024",
}

ALTTPRDE_DEFINITION = TournamentDefinition(
    event_slug="alttprde",
    racetime_category="alttpr",
    racetime_goal="Beat the game",
    guild_id=469300113290821632,
    audit_channel_id=473668481011679234,
    commentary_channel_id=469317757331308555,
    helper_role_ids=[534030648713674765, 469300493542490112, 623071415129866240],
    lang="de",
    stream_delay=10,
    create_scheduled_events=True,
)


class ALTTPRDEOrchestrator(ALTTPRTournamentOrchestrator):
    async def roll(self) -> SeedResult:
        return await self._roll_from_title_map(
            ALTTPRDE_TITLE_MAP, hints=False, spoilers="off", allow_quickswap=True
        )
