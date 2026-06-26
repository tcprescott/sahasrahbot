"""``TestOrchestrator`` — the debug ``test`` tournament, decomposed.

Mirrors the legacy ``test.TestTournament`` (which extended ``ALTTPR2024Race`` and only
overrode ``configuration()``): no seed roll, no per-race processing — just the
room-creation lifecycle. The hardcoded Discord IDs from the old ``configuration()``
move into ``TEST_DEFINITION``. This handler is gated to ``config.DEBUG`` in the
registry, so it never touches a production tournament.
"""

from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition

TEST_DEFINITION = TournamentDefinition(
    event_slug="test",
    racetime_category="test",
    racetime_goal="Beat the game",
    guild_id=508335685044928540,
    audit_channel_id=537469084527230976,
    announce_channel_id=508335685044928548,
)


class TestOrchestrator(TournamentOrchestrator):
    """The ``test`` event has no business overrides (matches the legacy TestTournament)."""
