"""``SMWDEOrchestrator`` — the SMW Hacks DE tournament, decomposed.

Mirrors the legacy ``smwde.SMWDETournament`` (which extended the base ``TournamentRace``
and only overrode ``configuration()``): a Super Mario World hacks event with no seed
roll and no per-race processing — just the room-creation lifecycle. It therefore
extends the base :class:`TournamentOrchestrator` (not the ALTTPR one), so ``!tournamentrace``
is a no-op exactly as before. The hardcoded Discord IDs move into ``SMWDE_DEFINITION``.
"""

from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition

SMWDE_DEFINITION = TournamentDefinition(
    event_slug="smwde",
    racetime_category="smw-hacks",
    racetime_goal="Any%",
    guild_id=753727862229565612,
    audit_channel_id=826775494329499648,
    scheduling_needs_channel_id=835946387065012275,
    helper_role_ids=[754845429773893782, 753742980820631562],
    lang="de",
)


class SMWDEOrchestrator(TournamentOrchestrator):
    """The ``smwde`` event has no business overrides (matches the legacy SMWDETournament)."""
