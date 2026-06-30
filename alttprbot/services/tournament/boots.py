"""``BootsOrchestrator`` — the ALTTPR Boots tournament, decomposed.

Mirrors the legacy ``boots.ALTTPRCASBootsTournamentRace`` (which extended
``ALTTPRTournamentRace`` and overrode only ``roll()`` + ``configuration()``): it rolls
the fixed ``casualboots`` preset with quickswap and inherits the whole ALTTPR seed-roll
lifecycle. The hardcoded Discord IDs from the old ``configuration()`` move into
``BOOTS_DEFINITION``.
"""

from alttprbot.services.seedgen import generator
from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

BOOTS_DEFINITION = TournamentDefinition(
    event_slug="boots",
    racetime_category="alttpr",
    racetime_goal="Beat the game - Tournament (Solo)",
    guild_id=973765801528139837,
    lang="en",
)


class BootsOrchestrator(ALTTPRTournamentOrchestrator):
    async def roll(self) -> SeedResult:
        seed = await generator.ALTTPRPreset("casualboots").generate(allow_quickswap=True)
        return SeedResult(seed=seed)
