"""Registry-unification guards for the service-tier ``registry`` module.

The hardcoded fallback (used when ``TOURNAMENT_CONFIG_ENABLED`` is false — the production
default) is derived from ``AVAILABLE_TOURNAMENT_HANDLERS`` so it can never dispatch a slug
to a different handler than the catalog / ``config/tournaments.yaml`` path. These tests pin
that single-source invariant and the current migration state against the entry-based
registry that replaced ``alttprbot/tournaments.py``.
"""

from alttprbot.services.tournament import registry
from alttprbot.services.tournament.registry import TournamentEntry


def test_hardcoded_fallback_never_drifts_from_catalog():
    # Every slug the hardcoded fallback activates must resolve to the SAME entry object
    # as the catalog — i.e. the fallback selects which slugs are active, never which class.
    for slug, entry in registry._HARDCODED_TOURNAMENT_DATA.items():
        assert entry is registry.AVAILABLE_TOURNAMENT_HANDLERS[slug], (
            f"hardcoded fallback for {slug!r} drifted from AVAILABLE_TOURNAMENT_HANDLERS"
        )


def test_active_hardcoded_slugs_exist_in_catalog():
    for slug in registry._HARDCODED_ACTIVE_SLUGS:
        assert slug in registry.AVAILABLE_TOURNAMENT_HANDLERS


def test_catalog_entries_bind_orchestrator_and_definition():
    # Every catalog value is a TournamentEntry pairing an orchestrator class with a definition.
    for slug, entry in registry.AVAILABLE_TOURNAMENT_HANDLERS.items():
        assert isinstance(entry, TournamentEntry), f"{slug} is not a TournamentEntry"
        assert isinstance(entry.orchestrator_cls, type)
        assert entry.definition is not None


def test_league_slugs_share_one_orchestrator_two_definitions():
    inv = registry.AVAILABLE_TOURNAMENT_HANDLERS["invleague"]
    opn = registry.AVAILABLE_TOURNAMENT_HANDLERS["alttprleague"]
    # One orchestrator class, two distinct definitions (invitational vs open).
    assert inv.orchestrator_cls is opn.orchestrator_cls
    assert inv.definition is not opn.definition
