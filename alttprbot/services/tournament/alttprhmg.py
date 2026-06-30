"""``ALTTPRHMGOrchestrator`` — the ALTTPR HMG tournament, decomposed.

Mirrors the legacy ``alttprhmg.ALTTPRHMGTournament`` (extends the ALTTPR family,
overrides only ``roll()`` + ``configuration()``): a fixed ``hmg`` preset on the ``live``
branch, tournament mode, no hints, spoilers off, with quickswap. Hardcoded IDs move into
``ALTTPRHMG_DEFINITION``.
"""

from alttprbot.services.seedgen import generator
from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

ALTTPRHMG_DEFINITION = TournamentDefinition(
    event_slug="alttprhmg",
    racetime_category="alttpr",
    racetime_goal="Beat the game (glitched)",
    guild_id=535946014037901333,
    audit_channel_id=850226062864023583,
    commentary_channel_id=549709098015391764,
    helper_role_ids=[549709214000480276, 535962854004883467, 535962802230132737],
)


class ALTTPRHMGOrchestrator(ALTTPRTournamentOrchestrator):
    async def roll(self) -> SeedResult:
        seed = await generator.ALTTPRPreset("hmg").generate(
            allow_quickswap=True, tournament=True, hints=False, spoilers="off", branch="live"
        )
        return SeedResult(seed=seed)
