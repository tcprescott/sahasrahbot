"""Tournament service tier (business).

Home of the decomposed tournament system (see
``docs/plans/tournament_decomposition.md``): the ``TournamentOrchestrator`` base +
per-event orchestrators, the presentation-neutral ``SeedResult`` hand-off, and the
``TournamentDefinition`` config value object that replaces the hardcoded Discord IDs
in the legacy ``alttprbot/tournament/`` god-object.

This package must never import ``discord``, ``racetime_bot``, ``quart``, or
``alttprbot.presentation`` — it reaches those surfaces through the
``alttprbot.services._notify`` gateways.
"""

from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

__all__ = ["SeedResult", "TournamentDefinition"]
