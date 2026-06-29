"""``NoLogicOrchestrator`` — the ALTTPR No Logic tournament, decomposed.

Mirrors the legacy ``nologic.ALTTPRNoLogicRace`` (extends the ALTTPR family, overrides
only ``roll()`` + ``configuration()``): a fixed ``nologic_rods`` preset on the ``beeta``
branch with quickswap. Hardcoded IDs move into ``NOLOGIC_DEFINITION``.
"""

from alttprbot.services.seedgen import generator
from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

NOLOGIC_DEFINITION = TournamentDefinition(
    event_slug="nologic",
    racetime_category="alttpr",
    racetime_goal="Beat the game (glitched)",
    guild_id=535946014037901333,
    audit_channel_id=850226062864023583,
    commentary_channel_id=549709098015391764,
    lang="en",
)


class NoLogicOrchestrator(ALTTPRTournamentOrchestrator):
    async def roll(self) -> SeedResult:
        seed = await generator.ALTTPRPreset("nologic_rods").generate(allow_quickswap=True, branch="beeta")
        return SeedResult(seed=seed)
